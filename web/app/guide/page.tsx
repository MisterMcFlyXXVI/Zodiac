export const metadata = { title: "How to read this · zbot" };

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
          <p className="mono">AENz0K0M0[NAM</p>
          <p className="small">April 1970. 13 symbols, only 8 different ones. Thousands of English phrases and names fit its repeat pattern.</p>
        </div>
        <div className="card">
          <h3>Z32: the Mt. Diablo map cipher</h3>
          <p className="mono">C9J|#Ok[AMf8?ORTG<br />X6FDVj%HCELzPW9</p>
          <p className="small">June 1970. 32 symbols, 29 different ones. Almost any English text of that length fits.</p>
        </div>
      </div>
      <p className="small muted">
        Z408 (solved 1969) and Z340 (solved 2020) are used only to prove the solver works. zbot recovers 97.5% and 97.1% of their
        letters from scratch.
      </p>

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

      <h2>What this is not</h2>
      <p>
        zbot does not identify anyone. A name that fits Z13&apos;s pattern is not evidence about a person: hundreds of names fit.
      </p>
    </>
  );
}
