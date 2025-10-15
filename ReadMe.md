# P11. Using LLM to Evaluate Query Plan

# Equivalence

## Approach Overview

1. Plan Conversion
    ○ Input PostgreSQL physical plans PA and PB.
    ○ Translate into Calcite-compatible logical relational algebra form
2. Using LLM to check Plan equivalence
    ○ Provide the RA representations of PA and PB to an LLM along with a restricted
       vocabulary of Calcite rules so that the transformations suggested by LLMs are
       available in the Calcite.
    ○ The LLM’s role is to act as a search tool:
       ■ Identify potential equivalence patterns between RA trees.
       ■ Propose a minimal sequence of transformations that could convert one
          plan into the other.
       ■ Output in a constrained, machine-readable format.
    ○ **This step reduces the otherwise huge transformation search space and**
       **focuses only on promising transformation paths**.
3. Calcite Verification
    ○ Validate that each LLM-suggested transformation exists in Calcite’s library of
       rules (Not really needed though, since we already have vocabulary restriction).
    ○ Apply the sequence step by step using Calcite’s deterministic engine.
    ○ If the resulting RA tree matches the target plan, equivalence is confirmed.
4. Equivalence Decision
    ○ True –> Plans successfully transformed into each other.
    ○ Don’t Know –> No valid transformation sequence found, or Calcite cannot
       confirm equivalence.

## LLM Component

```
● Base Model : Start with an existing LLM (preferably GPT4).
● Prompting : RA trees + rule vocabulary + request for JSON output.
● Constraint : Output strictly limited to Calcite’s vocabulary of transformations.
```

