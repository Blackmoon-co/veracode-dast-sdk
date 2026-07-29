// Scriptable Request Modification (SRM) example — adds an HMAC signature
// header to every outgoing request during an authenticated DAST scan.
//
// PLACEHOLDER: the exact global objects/function signature Veracode's DAST
// engine calls at scan time are not documented in this repo and could not
// be verified from Veracode's public docs in this session. Confirm the
// real API surface against Veracode's official "Example Script for
// Scriptable Request Modification Authentication" page before using this
// against a real scan — this file only exists to exercise the SDK's
// upload path (base64-encode -> PUT srm_authentication), which does not
// interpret or validate script contents.

function updateRequest(request) {
    var secretKey = "REPLACE_WITH_SCANNER_VARIABLE_REFERENCE"; // e.g. resolved via a Scanner Variable
    var timestamp = Date.now().toString();
    var payload = request.method + request.url + timestamp;
    var signature = hmac_sha256(secretKey, payload); // placeholder helper — confirm the real one Veracode exposes

    request.addHeader("X-Timestamp", timestamp);
    request.addHeader("X-HMAC-Signature", signature);

    return request;
}
