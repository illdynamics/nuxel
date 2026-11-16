p="/root/nuxel-build/neatvnc/src/auth/apple-dh.c"
s=open(p).read()
s=s.replace("\tuint8_t q[APPLE_DH_SERVER_KEY_LENGTH] = {};\n\tcrypto_key_p(pub, mod, sizeof(mod));\n\tcrypto_key_q(pub, q, sizeof(q));\n",
            "\tuint8_t q[APPLE_DH_SERVER_KEY_LENGTH] = {};\n\tcrypto_key_p(pub, mod, sizeof(mod));\n\tcrypto_key_q(pub, q, sizeof(q));\n\tfprintf(stderr, \"ARD send: g=%d key_size=%d mod=%02x%02x..%02x%02x q=%02x%02x..%02x%02x\\n\", crypto_key_g(client->apple_dh_secret), (int)sizeof(q), mod[0],mod[1],mod[254],mod[255], q[0],q[1],q[254],q[255]);\n")
s=s.replace('#include <assert.h>\n','#include <assert.h>\n#include <stdio.h>\n',1)
open(p,"w").write(s)
print("q-debug")
