p="/root/nuxel-build/neatvnc/src/auth/apple-dh.c"
s=open(p).read()
a=s.index("int apple_dh_send_public_key")
b=s.index("int apple_dh_handle_response")
send='''int apple_dh_send_public_key(struct nvnc_client* client)
{
	client->apple_dh_secret = crypto_keygen();
	assert(client->apple_dh_secret);

	struct crypto_key* pub =
		crypto_derive_public_key(client->apple_dh_secret);
	assert(pub);

	/* Apple's ARD exchange: BE16 generator, BE16 key_size, then exactly
	 * key_size bytes of modulus followed by exactly key_size bytes of public
	 * key.  Client implementations (Jump Desktop, Screen Sharing) read the
	 * announced key_size and then consume modulus+key of that length; the
	 * old code announced 64 (buffer size) while the key was shorter and the
	 * two ends never resynchronised. */
	uint8_t mod[APPLE_DH_MAX_KEY_LEN] = {};
	uint8_t key[APPLE_DH_MAX_KEY_LEN] = {};
	uint32_t mod_len = crypto_key_p(pub, mod, sizeof(mod));
	uint32_t key_len = crypto_key_q(pub, key, sizeof(key));
	if (mod_len == 0 || mod_len > APPLE_DH_MAX_KEY_LEN)
		return -1;
	if (key_len == 0 || key_len > APPLE_DH_MAX_KEY_LEN)
		return -1;
	if (mod_len < key_len) {
		/* left-pad modulus, never truncate */
		memmove(mod + (key_len - mod_len), mod, mod_len);
		memset(mod, 0, key_len - mod_len);
		mod_len = key_len;
	}
	if (key_len < mod_len) {
		memmove(key + (mod_len - key_len), key, key_len);
		memset(key, 0, mod_len - key_len);
		key_len = mod_len;
	}
	uint32_t klen = mod_len;

	uint16_t generator = htons((uint16_t)crypto_key_g(client->apple_dh_secret));
	uint16_t key_size = htons((uint16_t)klen);
	stream_write(client->net_stream, &generator, sizeof(generator));
	stream_write(client->net_stream, &key_size, sizeof(key_size));
	stream_write(client->net_stream, mod, klen);
	stream_write(client->net_stream, key, klen);

	crypto_key_del(pub);
	return 0;
}

'''
open(p,"w").write(s[:a]+send+s[b:])
print("patched2")
