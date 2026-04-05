# Kdc Systems

Mini ERP para gerenciar vendas, estoque, compras de fornecedores e relatórios.

## Instalação

1. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   ```
2. Ative o ambiente:
   - Windows PowerShell:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - Windows CMD:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
3. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o aplicativo:
   ```bash
   python app.py
   ```

## Uso

- Acesse `http://127.0.0.1:5000`
- Login padrão: `admin` / `admin123`
- O projeto já vem com formulários de cadastro para usuários, produtos, clientes, fornecedores, categorias e unidades.
- Interface de vendas com cálculo de total, desconto, acréscimo, troco e geração de código Pix.
- Relatórios por período, estoque, clientes principais, lucro por produto e vendas por forma de pagamento.
- Suporte a múltiplos idiomas (Português, Inglês, Espanhol, Francês, Alemão e Chinês).
- Manual de uso interno disponível no menu.

## Próximos passos

- Ajustar layouts ou adicionar temas visuais
- Conectar envio de e-mail real para fechamento de caixa
- Completar relatórios de perdas, devoluções e despesas fixas
