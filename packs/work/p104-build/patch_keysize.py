import re,os
p="/root/nuxel-build/neatvnc/src/crypto/nettle/key.c"
s=open(p).read()
s=re.sub(r'static void initialise_p\(mpz_t p\)\n\{.*?\n\}\n\nstatic void generate_random',
'''static void initialise_p(mpz_t p)
{
	/* TEST: RFC 2409 group 2 (1024-bit MODP), a real safe prime. */
	static const char s[] =
		"FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
		"29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
		"EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
		"E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
		"EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE65381"
		"FFFFFFFFFFFFFFFF";

	char buf[128];
	size_t len = 0;
	struct base16_decode_ctx ctx;
	nettle_base16_decode_init(&ctx);
	nettle_base16_decode_update(&ctx, &len, (uint8_t*)buf, sizeof(s) - 1, s);
	nettle_base16_decode_final(&ctx);
	assert(len == sizeof(buf));
	crypto_import(p, (const uint8_t*)buf, sizeof(buf));
}

static void generate_random''', s, flags=re.S)
open(p,"w").write(s)
print("key1024")
q="/root/nuxel-build/neatvnc/src/auth/apple-dh.c"
t=open(q).read()
t=t.replace("#define APPLE_DH_SERVER_KEY_LENGTH 256","#define APPLE_DH_SERVER_KEY_LENGTH 128")
open(q,"w").write(t)
print("klen128")
