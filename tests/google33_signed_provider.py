"""Real RSA provider JWTs and JWKS via HTTP transport, no mocked principal.

Private signing keys live only in each synthetic test's RAM. The application
runs its official Google verifier, canonical issuer/audience/expiry and binding.
"""
from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
import jwt


class SignedProvider:
    def __init__(self,monkeypatch,claims,*,status=200,observer=None):
        self.claims=claims;self.calls=[];self.status=status
        self.on_request=None
        self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.jwk=jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key(),as_dict=True)
        self.jwk.update(kid="synthetic33",use="sig",alg="RS256")
        # Nested provider fixtures must not capture an earlier monkeypatched
        # factory and silently replace this test's JWKS with another key.
        actual=httpx._client.AsyncClient
        def respond(request):
            assert request.url.scheme=="https" and request.url.host=="www.googleapis.com" and request.url.path=="/oauth2/v3/certs"
            assert not request.url.query
            if self.on_request is not None:self.on_request()
            self.calls.append(observer(claims,status) if observer else request.url.path)
            return httpx.Response(self.status,json={"keys":[self.jwk]})
        monkeypatch.setattr(httpx,"AsyncClient",lambda *args,**kwargs:actual(*args,**dict(kwargs,transport=httpx.MockTransport(respond))))

    def credential(self,*,claims=None,key=None,algorithm="RS256",kid="synthetic33"):
        return jwt.encode(self.claims if claims is None else claims,self.key if key is None else key,
            algorithm=algorithm,headers={"kid":kid})
