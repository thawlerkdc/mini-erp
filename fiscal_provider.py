from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import base64
import json
from typing import Any, Dict, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request


class FiscalProviderError(Exception):
    """Erro de comunicação/negócio no provedor fiscal."""


@dataclass
class FiscalCompanyConfig:
    account_id: int
    provider: str
    environment: str
    token_api: str
    cnpj: str = ""
    company_name: str = ""


class FiscalProvider(ABC):
    @abstractmethod
    def emitir_nota(self, venda: Dict[str, Any], empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def consultar_status(self, referencia: str, empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def cancelar_nota(self, chave: str, empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise NotImplementedError


class FocusNFeProvider(FiscalProvider):
    _BASE_BY_ENV = {
        "homologacao": "https://homologacao.focusnfe.com.br",
        "producao": "https://api.focusnfe.com.br",
    }

    def _base_url(self, environment: str) -> str:
        env = (environment or "homologacao").strip().lower()
        return self._BASE_BY_ENV.get(env, self._BASE_BY_ENV["homologacao"])

    def _auth_header(self, token_api: str) -> str:
        token = (token_api or "").strip()
        if not token:
            raise FiscalProviderError("Token da Focus NFe não configurado.")
        raw = f"{token}:".encode("utf-8")
        encoded = base64.b64encode(raw).decode("ascii")
        return f"Basic {encoded}"

    def _http_json(self, method: str, url: str, token_api: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body = None
        headers = {
            "Accept": "application/json",
            "Authorization": self._auth_header(token_api),
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib_request.Request(url=url, data=body, method=method.upper(), headers=headers)
        try:
            with urllib_request.urlopen(req, timeout=25) as response:
                text = response.read().decode("utf-8", errors="ignore")
                status_code = response.getcode()
                parsed = json.loads(text) if text.strip() else {}
                return {
                    "http_status": status_code,
                    "json": parsed,
                    "raw": text,
                }
        except urllib_error.HTTPError as exc:
            err_text = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
            raise FiscalProviderError(f"Focus HTTP {exc.code}: {err_text[:240]}")
        except urllib_error.URLError as exc:
            raise FiscalProviderError(f"Focus indisponível: {exc}")
        except Exception as exc:
            raise FiscalProviderError(f"Erro inesperado Focus: {exc}")

    def emitir_nota(self, venda: Dict[str, Any], empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        base = self._base_url(empresa.environment)
        referencia = str(venda.get("sale_id") or venda.get("referencia") or "").strip()
        if not referencia:
            raise FiscalProviderError("Referência da venda não informada para emissão.")

        note_type = str(venda.get("tipo_nota") or "NFCE").strip().upper()
        endpoint_type = "nfce" if note_type == "NFCE" else "nfe"
        endpoint = f"{base}/v2/{endpoint_type}"

        request_payload = {
            "referencia": referencia,
            "natureza_operacao": "Venda de mercadoria",
            "data_emissao": venda.get("data_emissao") or "",
            "serie": str(venda.get("serie") or "1"),
            "numero": int(venda.get("numero") or 1),
            "itens_nf": venda.get("itens_nf") or [],
            "metadata": {
                "sale_id": venda.get("sale_id"),
                "subtotal_produtos": venda.get("subtotal_produtos"),
                "desconto": venda.get("desconto"),
                "juros": venda.get("juros"),
                "total_final": venda.get("total_final"),
            },
        }

        response = self._http_json("POST", endpoint, empresa.token_api, payload=request_payload)
        data = response.get("json") or {}
        status = str(data.get("status") or "processando").strip().lower()

        return {
            "provider": "focus",
            "provider_reference": referencia,
            "status": "emitida" if status in {"autorizado", "autorizada", "emitida"} else ("pendente" if status in {"processando", "em_processamento"} else "erro"),
            "invoice_key": data.get("chave") or data.get("chave_acesso") or "",
            "xml": data.get("xml") or "",
            "pdf_url": data.get("danfe_url") or data.get("pdf_url") or "",
            "raw_response": response.get("raw") or "",
            "http_status": response.get("http_status"),
        }

    def consultar_status(self, referencia: str, empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        base = self._base_url(empresa.environment)
        ref = str(referencia or "").strip()
        if not ref:
            raise FiscalProviderError("Referência não informada para consulta de status.")

        endpoint = f"{base}/v2/nfe/{ref}"
        response = self._http_json("GET", endpoint, empresa.token_api)
        data = response.get("json") or {}
        status = str(data.get("status") or "desconhecido").strip().lower()

        return {
            "provider": "focus",
            "provider_reference": ref,
            "status": status,
            "invoice_key": data.get("chave") or data.get("chave_acesso") or "",
            "xml": data.get("xml") or "",
            "pdf_url": data.get("danfe_url") or data.get("pdf_url") or "",
            "raw_response": response.get("raw") or "",
            "http_status": response.get("http_status"),
        }

    def cancelar_nota(self, chave: str, empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        base = self._base_url(empresa.environment)
        key = str(chave or "").strip()
        if not key:
            raise FiscalProviderError("Chave da nota não informada para cancelamento.")

        endpoint = f"{base}/v2/nfe/{key}/cancelar"
        response = self._http_json("POST", endpoint, empresa.token_api, payload={"justificativa": "Cancelamento solicitado pelo ERP"})
        data = response.get("json") or {}

        return {
            "provider": "focus",
            "invoice_key": key,
            "status": str(data.get("status") or "cancelamento_solicitado").strip().lower(),
            "raw_response": response.get("raw") or "",
            "http_status": response.get("http_status"),
        }


class NFeIoProvider(FiscalProvider):
    def emitir_nota(self, venda: Dict[str, Any], empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise FiscalProviderError("Provider NFe.io ainda não implementado.")

    def consultar_status(self, referencia: str, empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise FiscalProviderError("Provider NFe.io ainda não implementado.")

    def cancelar_nota(self, chave: str, empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise FiscalProviderError("Provider NFe.io ainda não implementado.")


class TecnoSpeedProvider(FiscalProvider):
    def emitir_nota(self, venda: Dict[str, Any], empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise FiscalProviderError("Provider TecnoSpeed ainda não implementado.")

    def consultar_status(self, referencia: str, empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise FiscalProviderError("Provider TecnoSpeed ainda não implementado.")

    def cancelar_nota(self, chave: str, empresa: FiscalCompanyConfig) -> Dict[str, Any]:
        raise FiscalProviderError("Provider TecnoSpeed ainda não implementado.")


def create_fiscal_provider(provider_name: str) -> FiscalProvider:
    normalized = (provider_name or "focus").strip().lower()
    if normalized == "focus":
        return FocusNFeProvider()
    if normalized == "nfeio":
        return NFeIoProvider()
    if normalized == "tecnospeed":
        return TecnoSpeedProvider()
    return FocusNFeProvider()
