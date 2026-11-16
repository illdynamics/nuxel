p="/root/nuxel-build/neatvnc/src/auth/apple-dh.c"
s=open(p).read()
a=s.index("int apple_dh_handle_response")
# find 'update_min_rtt(client);' after a
b=s.index("	update_min_rtt(client);", a)
body='''int apple_dh_handle_response(struct nvnc_client* client)
{
	struct rfb_apple_dh_client_msg* msg =
	        (void*)(client->msg_buffer + client->buffer_index);

	uint8_t p[APPLE_DH_SERVER_KEY_LENGTH] = {};
	crypto_key_p(client->apple_dh_secret, p, sizeof(p));

	// Client wire format: encrypted_credentials[128] | public key (fixed size)
	if (client->buffer_len - client->buffer_index <
			sizeof(*msg) + APPLE_DH_SERVER_KEY_LENGTH)
		return 0;

	int g = crypto_key_g(client->apple_dh_secret);

	struct crypto_key* remote_key = crypto_key_new(g, p, sizeof(p),
			msg->public_key, APPLE_DH_SERVER_KEY_LENGTH);
	assert(remote_key);

	struct crypto_key* shared_secret =
		crypto_derive_shared_secret(client->apple_dh_secret, remote_key);
	assert(shared_secret);
	crypto_key_del(remote_key);

	uint8_t shared_buf[APPLE_DH_SERVER_KEY_LENGTH];
	crypto_key_q(shared_secret, shared_buf, sizeof(shared_buf));
	crypto_key_del(shared_secret);

	uint8_t hash[16] = {};
	crypto_hash_one(hash, sizeof(hash), CRYPTO_HASH_MD5, shared_buf,
			sizeof(shared_buf));

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
s=s.replace("#define APPLE_DH_KEY_BUF 512\n#define APPLE_DH_MAX_KEY_LEN 256\n","#define APPLE_DH_SERVER_KEY_LENGTH 256\n")
s=s.replace("\treturn sizeof(*msg) + APPLE_DH_CLIENT_KEY_LEN_FIELD + key_len;","\treturn sizeof(*msg) + APPLE_DH_SERVER_KEY_LENGTH;")
open(p,"w").write(s)
print("apple-final")
