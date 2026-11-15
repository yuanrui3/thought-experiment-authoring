// Dev helper: print a judge prompt and an audit prompt from a generated workflow script.
const fs = require('fs')
let s = fs.readFileSync(process.argv[2], 'utf8')
s = s.replace('export const meta', 'const meta').replace(/const thunks = \[\][\s\S]*$/, '')
s += '\n;globalThis.__P = { j: judgePrompt(BATCHES[0]), a: AUDITS.length ? auditPrompt(AUDITS[0]) : "" }'
eval(s)
const { j, a } = globalThis.__P
console.log(j.slice(0, 2100)); console.log('\n[...]\n'); console.log(j.slice(-330))
console.log('\n[judge prompt chars]', j.length, '[audit prompt chars]', a.length)
if (a) { const i = a.indexOf('PAIR P01'); console.log('\n' + a.slice(i, i + 1700)) }
