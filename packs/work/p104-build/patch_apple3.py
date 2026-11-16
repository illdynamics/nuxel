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

	/* Upstream framing: BE16 generator, BE16 key_size (= 256 for the RFC 3526
	 * group 5 modulus used by crypto_keygen()), then the modulus and the
	 * public key, each exactly APPLE_DH_SERVER_KEY_LENGTH bytes, big-endian
	 * and left-padded with zeros.  Both sides must agree on this fixed size. */
	uint8_t mod[APPLE_DH_SERVER_KEY_LENGTH] = {};
	uint8_t q[APPLE_DH_SERVER_KEY_LENGTH] = {};
	crypto_key_p(pub, mod, sizeof(mod));
	crypto_key_q(pub, q, sizeof(q));

	struct rfb_apple_dh_server_msg msg = {
		.generator = htons(crypto_key_g(client->apple_dh_secret)),
		.key_size = htons(sizeof(q)),
	};

	stream_write(client->net_stream, &msg, sizeof(msg));
	stream_write(client->net_stream, mod, sizeof(mod));
	stream_write(client->net_stream, q, sizeof(q));

	crypto_key_del(pub);
	return 0;
}

'''
s=s[:a]+send+s[b:]
open(p,"w").write(s)
print("apple3")
