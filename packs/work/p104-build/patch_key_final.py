p="/root/nuxel-build/neatvnc/src/crypto/nettle/key.c"
s=open(p).read()
a=s.index("static void initialise_p(mpz_t p)")
b=s.index("struct crypto_key* crypto_keygen(void)")
new='''static void initialise_p(mpz_t p)
{
	/* RFC 3526, section 3 (1536-bit MODP, group 5) - same group upstream
	 * neatvnc uses for Apple ARD.  Earlier Nuxel builds replaced this with a
	 * hand-typed 128-bit constant in an attempt to satisfy Jump Desktop's
	 * "key is too big" error; that is not a safe prime and desynchronised the
	 * exchange.  Keep the standard group and the standard 256-byte framing. */
	static const char s[] =
		"FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
		"29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
		"EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
		"E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
		"EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
		"C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
		"83655D23DCA3AD961C62F356208552BB9ED529077096966D"
		"670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
		"E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
		"DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
		"15728E5A8AACAA68FFFFFFFFFFFFFFFF";

	char buf[256];
	size_t len = sizeof(buf);
	struct base16_decode_ctx ctx;
	nettle_base16_decode_init(&ctx);
	nettle_base16_decode_update(&ctx, &len, (uint8_t*)buf, sizeof(s) - 1, s);
	nettle_base16_decode_final(&ctx);
	assert(len == sizeof(buf));

	crypto_import(p, (const uint8_t*)buf, sizeof(buf));
}

static void generate_random(mpz_t n)
{
	uint8_t buf[256];
	crypto_random(buf, sizeof(buf));
	crypto_import(n, buf, sizeof(buf));
}

'''
open(p,"w").write(s[:a]+new+s[b:])
print("key-final")
