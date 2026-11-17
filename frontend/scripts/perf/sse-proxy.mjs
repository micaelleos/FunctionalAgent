// Proxy de medição (F08-RT-06): repassa à API local; o POST de mensagens vira 5000 tokens em SSE.
import http from 'node:http'
const UP = 'http://localhost:8000',
  N = 5000,
  EVERY_MS = 2
const cors = {
  'Access-Control-Allow-Origin': 'http://localhost:5174',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type, Accept',
  'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE',
  'Access-Control-Expose-Headers': 'X-Conversation-Id',
}
const words =
  process.env.MODE === 'table'
    ? ['| CA', '| principal', '| Dado', 'que', 'o', 'cliente', 'paga', '|\n']
    : [
        'Dado',
        'que',
        'o',
        '**cliente**',
        'escolhe',
        'Pix,',
        'quando',
        'confirma',
        'então',
        'vê',
        'o',
        'QR\n\n- item\n',
      ]
http
  .createServer(async (req, res) => {
    if (req.method === 'OPTIONS') return res.writeHead(204, cors).end()
    if (req.method === 'POST' && /\/messages$/.test(req.url)) {
      res.writeHead(200, {
        ...cors,
        'Content-Type': 'text/event-stream',
        'X-Conversation-Id': 'perf',
      })
      let i = 0
      const t = setInterval(() => {
        for (let k = 0; k < 2 && i < N; k++, i++)
          res.write(
            `event: token\ndata: ${JSON.stringify({ text: words[i % words.length] + ' ' })}\n\n`,
          )
        if (i >= N) {
          clearInterval(t)
          res.end(
            'event: done\ndata: {"usage":{"input_tokens":0,"output_tokens":5000,"cost_usd":0}}\n\n',
          )
        }
      }, EVERY_MS * 2)
      return
    }
    const body = await new Promise((r) => {
      const c = []
      req.on('data', (d) => c.push(d))
      req.on('end', () => r(Buffer.concat(c)))
    })
    const up = await fetch(UP + req.url, {
      method: req.method,
      headers: {
        authorization: req.headers.authorization ?? '',
        'content-type': req.headers['content-type'] ?? 'application/json',
      },
      body: ['GET', 'HEAD'].includes(req.method) ? undefined : body,
    })
    res.writeHead(up.status, {
      ...cors,
      'Content-Type': up.headers.get('content-type') ?? 'application/json',
    })
    res.end(Buffer.from(await up.arrayBuffer()))
  })
  .listen(8010)
