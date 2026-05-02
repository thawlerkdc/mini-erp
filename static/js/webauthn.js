(function () {
  'use strict';

  function toBase64Url(uint8) {
    var binary = '';
    for (var i = 0; i < uint8.byteLength; i += 1) {
      binary += String.fromCharCode(uint8[i]);
    }
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  }

  function fromBase64Url(base64url) {
    var padded = base64url.replace(/-/g, '+').replace(/_/g, '/');
    while (padded.length % 4) {
      padded += '=';
    }
    var binary = atob(padded);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  function normalizeCreationOptions(publicKey) {
    var options = JSON.parse(JSON.stringify(publicKey || {}));
    if (options.challenge) {
      options.challenge = fromBase64Url(options.challenge);
    }
    if (options.user && options.user.id) {
      options.user.id = fromBase64Url(options.user.id);
    }
    if (Array.isArray(options.excludeCredentials)) {
      options.excludeCredentials = options.excludeCredentials.map(function (item) {
        var clone = Object.assign({}, item);
        if (clone.id) {
          clone.id = fromBase64Url(clone.id);
        }
        return clone;
      });
    }
    return options;
  }

  function normalizeRequestOptions(publicKey) {
    var options = JSON.parse(JSON.stringify(publicKey || {}));
    if (options.challenge) {
      options.challenge = fromBase64Url(options.challenge);
    }
    if (Array.isArray(options.allowCredentials)) {
      options.allowCredentials = options.allowCredentials.map(function (item) {
        var clone = Object.assign({}, item);
        if (clone.id) {
          clone.id = fromBase64Url(clone.id);
        }
        return clone;
      });
    }
    return options;
  }

  function registrationCredentialToJSON(credential) {
    return {
      id: credential.id,
      rawId: toBase64Url(new Uint8Array(credential.rawId)),
      type: credential.type,
      response: {
        clientDataJSON: toBase64Url(new Uint8Array(credential.response.clientDataJSON)),
        attestationObject: toBase64Url(new Uint8Array(credential.response.attestationObject)),
        transports: (typeof credential.response.getTransports === 'function')
          ? credential.response.getTransports()
          : []
      }
    };
  }

  function authenticationCredentialToJSON(credential) {
    return {
      id: credential.id,
      rawId: toBase64Url(new Uint8Array(credential.rawId)),
      type: credential.type,
      response: {
        clientDataJSON: toBase64Url(new Uint8Array(credential.response.clientDataJSON)),
        authenticatorData: toBase64Url(new Uint8Array(credential.response.authenticatorData)),
        signature: toBase64Url(new Uint8Array(credential.response.signature)),
        userHandle: credential.response.userHandle
          ? toBase64Url(new Uint8Array(credential.response.userHandle))
          : null
      }
    };
  }

  function isSupported() {
    return !!(window.isSecureContext && window.PublicKeyCredential && navigator.credentials);
  }

  async function fetchJson(url, options) {
    var response = await fetch(url, Object.assign({
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    }, options || {}));

    var data = null;
    try {
      data = await response.json();
    } catch (e) {
      data = null;
    }

    if (!response.ok || !data || data.ok === false) {
      var message = (data && data.message) || 'Falha na operação WebAuthn.';
      throw new Error(message);
    }

    return data;
  }

  async function register() {
    if (!isSupported()) {
      throw new Error('WebAuthn indisponível neste dispositivo.');
    }

    var optionsResult = await fetchJson('/webauthn/register/options', {
      method: 'POST',
      body: JSON.stringify({})
    });

    var challenge = optionsResult.publicKey && optionsResult.publicKey.challenge;
    var creationOptions = normalizeCreationOptions(optionsResult.publicKey);

    var credential = await navigator.credentials.create({
      publicKey: creationOptions
    });

    if (!credential) {
      throw new Error('Não foi possível criar a credencial biométrica.');
    }

    var verifyResult = await fetchJson('/webauthn/register/verify', {
      method: 'POST',
      body: JSON.stringify({
        challenge: challenge,
        credential: registrationCredentialToJSON(credential)
      })
    });

    try {
      localStorage.setItem('mini_erp_webauthn_enabled', '1');
    } catch (e) {
      // ignore storage failures
    }

    return verifyResult;
  }

  async function login() {
    if (!isSupported()) {
      throw new Error('WebAuthn indisponível neste dispositivo.');
    }

    var optionsResult = await fetchJson('/webauthn/login/options', {
      method: 'POST',
      body: JSON.stringify({})
    });

    var challenge = optionsResult.publicKey && optionsResult.publicKey.challenge;
    var requestOptions = normalizeRequestOptions(optionsResult.publicKey);

    var credential = await navigator.credentials.get({
      publicKey: requestOptions
    });

    if (!credential) {
      throw new Error('Autenticação cancelada.');
    }

    return fetchJson('/webauthn/login/verify', {
      method: 'POST',
      body: JSON.stringify({
        challenge: challenge,
        credential: authenticationCredentialToJSON(credential)
      })
    });
  }

  window.MiniERPWebAuthn = {
    isSupported: isSupported,
    register: register,
    login: login
  };
})();
