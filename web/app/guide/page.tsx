import Glyph, { CipherGlyphs } from "@/components/Glyph";
import { GLYPHS } from "@/lib/glyphs";

export const metadata = { title: "How to read this · zbot" };

const Z13 = "AENz0K0M0[NAM";
const Z32 = "C9J|#Ok[AMf8?ORTGX6FDVj%HCELzPW9";

export default function Guide() {
  return (
    <>
      <h1>How to read this</h1>
      <p className="lede">
        The short version: any solver will print fluent-looking text for Z13 or Z32. That alone means nothing. zbot&apos;s job is to
        measure whether a result means anything, and most of the time the honest answer is &ldquo;it can&apos;t tell&rdquo;.
      </p>

      <h2>The ciphers</h2>
      <div className="grid two">
        <div className="card">
          <h3>Z13: &ldquo;My name is …&rdquo;</h3>
          <CipherGlyphs text={Z13} />
          <p className="small">April 1970. 13 symbols, only 8 different ones. Thousands of English phrases and names fit its repeat pattern.</p>
        </div>
        <div className="card">
          <h3>Z32: the Mt. Diablo map cipher</h3>
          <CipherGlyphs text={Z32} rows={[17, 15]} />
          <p className="small">June 1970. 32 symbols, 29 different ones. Almost any English text of that length fits.</p>
        </div>
      </div>
      <p className="small muted">
        Z408 (solved 1969) and Z340 (solved 2020) are used only to prove the solver works. zbot recovers 97.5% and 97.1% of their
        letters from scratch.
      </p>

      <h2>The symbols, and their codes</h2>
      <p className="small">
        The bot names each glyph with a keyboard character (David Oranchak&apos;s standard scheme, also used by AZdecrypt, the
        solver that cracked Z340). Only <em>which positions share a symbol</em> matters to the solver, never the shape, so the
        names don&apos;t affect results. The drawings here are approximations from written descriptions of the scans, not
        tracings. Hover over any glyph to see its description.
      </p>
      <details>
        <summary className="small">Show the key ({Object.keys(GLYPHS).length} glyphs)</summary>
        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table className="glyph-key">
            <thead><tr><th>Glyph</th><th>Code</th><th>Description</th><th className="num">In Z13</th><th className="num">In Z32</th></tr></thead>
            <tbody>
              {[...new Set([...Z13, ...Z32]), ...Object.keys(GLYPHS).filter((c) => !Z13.includes(c) && !Z32.includes(c))]
                .map((code) => [code, GLYPHS[code]] as const).filter(([, g]) => g).map(([code, g]) => (
                <tr key={code}>
                  <td><Glyph code={code} size={26} /></td>
                  <td className="mono">{code}</td>
                  <td className="small">{g.desc}</td>
                  <td className="num">{[...Z13].filter((c) => c === code).length || ""}</td>
                  <td className="num">{[...Z32].filter((c) => c === code).length || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <h2>What each test does</h2>
      <ol>
        <li><strong>Search the real cipher.</strong> Find the key that makes it read most like real text, under the hypothesis being tested.</li>
        <li><strong>Search shuffled copies.</strong> Scramble the cipher&apos;s own symbols into a random order and search those the same way. If the real cipher scores no better, nothing was found.</li>
        <li><strong>Search genuine text.</strong> Encipher real text so it has exactly the same repeat pattern, and search that the same way. If genuine text doesn&apos;t stand out either, the test was never able to find anything.</li>
      </ol>

      <h2>The numbers</h2>
      <dl className="explain">
        <dt>p</dt>
        <dd>The share of shuffled copies that scored at least as well as the real cipher. Small (under 0.05) means the real cipher stood out.</dd>
        <dt>p (Holm)</dt>
        <dd>The same, corrected for the fact that the bot has run many tests. Try 100 ideas and about 5 will reach p &lt; 0.05 by luck alone; this correction removes that. This is the number that matters.</dd>
        <dt>power</dt>
        <dd>How often genuine text, enciphered the same way, beat the shuffled copies. Below 0.2 the test is <em>untestable</em>: it couldn&apos;t have found anything, so its p means nothing either way.</dd>
        <dt>z</dt>
        <dd>How far the real cipher&apos;s score is from the shuffled copies&apos; average, in standard deviations. Calibrations reach z ≈ 24; nothing on Z13 or Z32 comes close.</dd>
        <dt>Alert</dt>
        <dd>p (Holm) below 0.05 <em>and</em> power at least 0.5. Even an alert is a lead for a human to check (does it hold under other transcriptions? does the text mean something?), not a solution.</dd>
      </dl>

      <h2>Why most results are &ldquo;untestable&rdquo;</h2>
      <p>
        Every cipher has a <em>unicity distance</em>: the length below which many different texts fit equally well. For Zodiac-style
        keys it is roughly 20–30 symbols. Z13 is below it and Z32 is at the edge, so a computer can always find a fluent reading, and
        so can a person. More computing power doesn&apos;t change that; new information would: better scans, more text under the same
        key, or Zodiac&apos;s worksheets.
      </p>

      <h2>Giving the bot ideas</h2>
      <p>
        On <a href="/queue">Queue &amp; ideas</a> you can queue the bot&apos;s own suggestions or describe a new test. Good ideas are
        specific and come with a reason: a transcription question, a key Zodiac might have reused, a reading order with precedent in
        Z340. Each test costs a little statistical credibility (see p (Holm)), so a few well-motivated tests beat many random ones.
      </p>

      <h2>What we&apos;ve learned so far</h2>
      <p>
        Measured on genuine test ciphers built like Z32, the solver finds readings that score <em>higher</em> than the true
        message in 12 of 12 cases. So the ciphers don&apos;t resist because the search is weak; with this much freedom in the
        key, many readings are more &ldquo;English&rdquo; than the real one. Scoring whole words raised Z32&apos;s power from about
        0.07 to about 0.2–0.28, which is why some tests use it. The full measurements, including what didn&apos;t work, are in
        the <a href="https://github.com/MisterMcFlyXXVI/Zodiac/blob/HEAD/results/FINDINGS.md" target="_blank" rel="noreferrer">research log ↗</a>.
      </p>

      <h2>What this is not</h2>
      <p>
        zbot does not identify anyone. A name that fits Z13&apos;s pattern is not evidence about a person: hundreds of names fit.
      </p>
    </>
  );
}
