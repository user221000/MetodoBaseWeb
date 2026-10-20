'use strict';
module.exports={sessionVersion(token){return JSON.parse(Buffer.from(token.split('.')[1],'base64url')).sv;}};
