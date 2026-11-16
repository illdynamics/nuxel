p="/root/nuxel-build/neatvnc/src/auth/apple-dh.c"
s=open(p).read()
s=s.replace('#include "auth/apple-dh.h"\n', '#include "auth/apple-dh.h"\n#include "auth/auth.h"\n\n#include <string.h>\n',1)
a=s.index("int apple_dh_send_public_key")
b=s.index("int apple_dh_handle_response")
send='''int apple_dh_send_public_key(struct nvnc_client* client)
{
	client->apple_dh_secret = crypto_keygen();
	assert(client->apple_dh_secret);

	struct crypto_key* pub =
		crypto_derive_public_key(client->apple_dh_secret);
	assert(pub);

	/* Apple's ARD key exchange sends the generator (BE16), the exact length
	 * of the modulus AND of the public key (BE16, both equal for a safe
	 * prime), followed by the modulus and the public key with those exact
	 * lengths.  The old code passed a 64-byte buffer to crypto_key_q() and
	 * advertised 64 bytes even though the key was shorter, which desynced
	 * the stream and made clients time out. */
	uint8_t mod[APPLE_DH_KEY_BUF] = {};
	uint8_t key[APPLE_DH_KEY_BUF] = {};
	uint32_t mod_len = crypto_key_p(pub, mod, sizeof(mod));
	uint32_t key_len = crypto_key_q(pub, key, sizeof(key));
	assert(mod_len > 0 && mod_len <= APPLE_DH_MAX_KEY_LEN);
	assert(key_len > 0 && key_len <= APPLE_DH_MAX_KEY_LEN);

	uint16_t generator = htons((uint16_t)crypto_key_g(client->apple_dh_secret));
	uint16_t key_size = htons((uint16_t)key_len);
	stream_write(client->net_stream, &generator, sizeof(generator));
	stream_write(client->net_stream, &key_size, sizeof(key_size));
	stream_write(client->net_stream, mod, mod_len);
	stream_write(client->net_stream, key, key_len);

	crypto_key_del(pub);
	return 0;
}

'''
s=s[:a]+send+s[b:]
# replace the body from p_len to crypto_cipher_del
a=s.index("	int p_len = crypto_key_p(client->apple_dh_secret")
b=s.index("	update_min_rtt(client);")
body='''	uint8_t p[APPLE_DH_KEY_BUF];
	uint32_t p_len = crypto_key_p(client->apple_dh_secret, p, sizeof(p));
	if (p_len == 0 || p_len > APPLE_DH_MAX_KEY_LEN)
		return -1;

	// Client wire format: encrypted_credentials[128] | public_key_len(BE16) | key
	if (client->buffer_len - client->buffer_index <
			sizeof(*msg) + APPLE_DH_CLIENT_KEY_LEN_FIELD)
		return 0;

	const uint8_t* len_field = msg->public_key;
	unsigned key_len = ((unsigned)len_field[0] << 8) | len_field[1];
	if (key_len == 0 || key_len > APPLE_DH_MAX_KEY_LEN) {
		/* Some clients omit the explicit length; the key then runs to the
		 * end of the message buffer. */
		key_len = (unsigned)(client->buffer_len - client->buffer_index
				- sizeof(*msg) - APPLE_DH_CLIENT_KEY_LEN_FIELD);
		if (key_len == 0 || key_len > APPLE_DH_MAX_KEY_LEN)
			return -1;
	}

	if (client->buffer_len - client->buffer_index <
			sizeof(*msg) + APPLE_DH_CLIENT_KEY_LEN_FIELD + key_len)
		return 0;

	int g = crypto_key_g(client->apple_dh_secret);

	struct crypto_key* remote_key = crypto_key_new(g, p, p_len,
			len_field + APPLE_DH_CLIENT_KEY_LEN_FIELD, key_len);
	if (!remote_key)
		return -1;

	struct crypto_key* shared_secret =
		crypto_derive_shared_secret(client->apple_dh_secret, remote_key);
	crypto_key_del(remote_key);
	if (!shared_secret)
		return -1;

	uint8_t shared_buf[APPLE_DH_KEY_BUF];
	uint32_t shared_len = crypto_key_q(shared_secret, shared_buf,
			sizeof(shared_buf));
	crypto_key_del(shared_secret);
	if (shared_len == 0 || shared_len > APPLE_DH_MAX_KEY_LEN)
		return -1;

	/* Apple's ARD KDF: MD5 over the raw shared secret (the exact bytes of
	 * the shared value, not zero-padded to a fixed length). */
	uint8_t hash[16] = {};
	crypto_hash_one(hash, sizeof(hash), CRYPTO_HASH_MD5, shared_buf,
			shared_len);

	struct crypto_cipher* cipher;
	cipher = crypto_cipher_new(NULL, hash, CRYPTO_CIPHER_AES128_ECB);
	assert(cipher);

	char username[128] = {};
	char* password = username + 64;

	crypto_cipher_decrypt(cipher, (uint8_t*)username, NULL,
			msg->encrypted_credentials, sizeof(username), NULL, 0);
	username[63] = '\\0';
	username[127] = '\\0';
	crypto_cipher_del(cipher);

'''
s=s[:a]+body+s[b:]
# buffer size constants
s=s.replace("#define APPLE_DH_SERVER_KEY_LENGTH 64\n", "#define APPLE_DH_KEY_BUF 512\n#define APPLE_DH_MAX_KEY_LEN 256\n")
s=s.replace("#include <string.h>\n","#include <string.h>\n#include <assert.h>\n",1)
open(p,"w").write(s)
print("apple patched")
