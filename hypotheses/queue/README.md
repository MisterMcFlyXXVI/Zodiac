# Adding a hypothesis

Drop a JSON file here. The bot picks it up on its next loop, after the
built-in queue. Fields are documented at the top of `zbot/hypotheses.py`.

Write down *before* running it why the idea is worth testing, and make
the family no bigger than it needs to be: the bot pays for every order and
pin set it tries, both in the null model and in the multiple-comparison
correction across all hypotheses.

Example (`example.json.disabled`, rename to `.json` to queue it):

```json
{
  "id": "user.z13.circles_distinct.simple",
  "title": "Z13 with three distinct circles, simple substitution",
  "motivation": "winchxyz F2: the pattern alone favours distinct circles by 10^2 to 10^4.5.",
  "cipher": "z13.circles_distinct",
  "model": "simple"
}
```
