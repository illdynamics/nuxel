# Nuxel Authenticator + Microsoft Entra (standard OATH/TOTP)

Nuxel Authenticator can generate standard RFC 6238 TOTP codes for an Entra work
account **only when the tenant's authentication-method policy permits software
OATH tokens**.

## Enrollment

1. Open the Entra **Security info** portal (or the organization's approved
   enrollment page) on a trusted device.
2. Add a sign-in method and choose **Authenticator app** / **software OATH
   token**, depending on what the tenant exposes.
3. When Entra offers a QR code or a setup key, use Nuxel Authenticator:
   - Scan QR with camera, or
   - Import QR image, or
   - Paste the `otpauth://totp/...` URI / enter the Base32 key manually.
4. Confirm the issuer, account, algorithm, digits and period preview.
5. Add the account and enter the current code when Entra asks to verify it.

## What this cannot do

Nuxel Authenticator is not Microsoft Authenticator and does not claim:

- push approval or number matching;
- passwordless phone sign-in / broker or PRT issuance;
- Microsoft Authenticator device registration;
- Intune compliance or Conditional Access device claims;
- Microsoft Authenticator passkey storage or attestation.

Do not reverse-engineer or impersonate Microsoft push protocols. Confirm tenant
policy and Conditional Access requirements with IT.
