// Local broker transport only. Preserve SDK AbortSignal without Node fetch's
// unrelated 300-second response-header deadline. No credential or web access.
import http from 'node:http';
import { Readable } from 'node:stream';

export function brokerFetch(input, init) {
  const request = new Request(input, init);
  const url = new URL(request.url);
  if (url.origin !== 'http://127.0.0.1:8765') {
    return Promise.reject(new TypeError('Kimi transport allows only the local broker'));
  }
  return new Promise((resolve, reject) => {
    const outgoing = http.request(url, {
      method: request.method,
      headers: Object.fromEntries(request.headers),
      signal: request.signal,
    }, response => {
      const headers = new Headers();
      for (let i = 0; i < response.rawHeaders.length; i += 2) {
        headers.append(response.rawHeaders[i], response.rawHeaders[i + 1]);
      }
      const status = response.statusCode;
      const noBody = request.method === 'HEAD' || [204, 205, 304].includes(status);
      resolve(new Response(noBody ? null : Readable.toWeb(response), {
        status, statusText: response.statusMessage, headers,
      }));
      if (noBody) response.resume();
    });
    outgoing.on('error', reject);
    if (request.body === null) outgoing.end();
    else request.arrayBuffer().then(body => outgoing.end(Buffer.from(body)), error => {
      outgoing.destroy();
      reject(error);
    });
  });
}

const originalFetch = globalThis.fetch;
globalThis.fetch = (input, init) => {
  const url = new URL(input instanceof Request ? input.url : String(input));
  return url.origin === 'http://127.0.0.1:8765'
    ? brokerFetch(input, init) : originalFetch(input, init);
};
