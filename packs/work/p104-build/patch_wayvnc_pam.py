p="/root/nuxel-build/wayvnc/src/main.c"
s=open(p).read()
old='''#ifdef ENABLE_PAM
	if (self->cfg.enable_pam) {
		if (!username || !password)
			return false;
		return pam_auth(username, password);
	}
#endif'''
new='''#ifdef ENABLE_PAM
	if (self->cfg.enable_pam) {
		/* Legacy DES (RFB 3.3) has no username field, so a DES response
		 * must be checked against the configured password.  PAM only owns
		 * the username-bearing methods (VeNCrypt, RSA-AES, Apple DH). */
		if (!username && password && cfg_password[0])
			return nvnc_auth_creds_verify(credentials, cfg_password);
		if (!username || !password)
			return false;
		return pam_auth(username, password);
	}
#endif'''
assert old in s
open(p,"w").write(s.replace(old,new))
print("patched wayvnc pam/des")
