# Nuxel Authenticator + Microsoft Entra (standard software OATH/TOTP)

Nuxel Authenticator can generate standard RFC 6238 TOTP codes for a Microsoft
Entra work/school account **only when the tenant's Authentication Methods policy
permits third-party software OATH tokens**. Microsoft documents OATH TOTP as an
open standard and supports third-party OATH TOTP applications, but a tenant
administrator can disable that method.

This is **not** Microsoft Authenticator and it does not implement any Microsoft
proprietary protocol.

## What works

- Standard `otpauth://totp/` secrets supplied by Entra's software-OATH enrollment
  flow, including SHA-1/SHA-256/SHA-512, 6 or 8 digits and 30 s or 60 s periods.
- QR camera scan, QR image import, pasted setup URI or manual Base32 entry.
- The code is generated locally and never leaves the device.

## Enrollment

1. On a trusted device/browser, open your organization's Microsoft Entra
   **Security info** page (or the enrollment page IT gave you). Do not enter
   your work password into Nuxel Authenticator.
2. Add a sign-in method and choose the option that explicitly permits a
   **third-party authenticator** or **software OATH token**. The wording varies
   by tenant configuration.
3. When Entra shows a QR code or setup key, use Nuxel Authenticator:
   - scan the QR with the camera,
   - import the QR image, or
   - paste the standard `otpauth://totp/...` URI / enter the Base32 key.
4. Confirm the preview: issuer, account, algorithm, digits and period. Do not
   blindly override values that Entra supplied.
5. Enter the current generated code into Microsoft's enrollment page. Only
   Microsoft can confirm whether the tenant accepted the registration; Nuxel
   cannot.

## Tenant-policy limits

If your organization disables third-party OATH, requires Microsoft Authenticator
push or number matching, requires device registration/Primary Refresh Token,
requires Intune compliance, or requires a phishing-resistant method (FIDO2,
Windows Hello, certificate-based authentication or passkeys), stop and contact
IT for an approved method.

Standard TOTP is **not phishing-resistant**. It may not satisfy a Conditional
Access policy that explicitly requires phishing-resistant authentication.

## What this cannot do

Nuxel Authenticator does not and will not:

- receive or approve Microsoft Authenticator push notifications;
- perform number matching;
- perform passwordless phone sign-in or broker/PRT flows;
- register a device with Entra or Intune;
- claim Conditional Access device trust or compliance;
- store or attest Microsoft Authenticator passkeys;
- reverse-engineer, imitate or impersonate Microsoft registration/push
  protocols.

## Official references

- OATH tokens: https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-oath-tokens
- Manage third-party software OATH tokens: https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-mfa-manage-oath-tokens
- Authentication methods policy: https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-authentication-methods-manage
- Microsoft Authenticator method: https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-authenticator-app
