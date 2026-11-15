export const meta = {
  name: 'te-authoring',
  description: 'Four Claude tiers each author five original vignette pairs (one per target factor) from an identical brief',
  phases: [{ title: 'Author', detail: 'one fresh-context agent per tier, identical brief' }],
}

const BRIEF = `You are an author in a benchmark called "Thought-experiment authoring". The benchmark tests whether an author can design a philosophical thought experiment that actually works when real readers judge it.

YOUR TASK
For each of the five target factors below, write one original vignette pair: five pairs in total, one per factor.

A vignette pair consists of:
1. Version A and version B: two short scenarios of at most 150 words each (a word is any whitespace-separated token; the limit is strict). The two versions must be identical, word for word, except for the text that has to change in order to vary the one target factor. Everything else that could move a reader's judgment must be the same in both versions: the outcome and how bad or good it is, what the people involved know and want, the probabilities and effort involved, who is affected, how vivid or emotional the wording is, and the length. Any difference other than the target factor is a confound and lowers your score.
2. One judgment question, identical for both versions, answered on a scale from 1 to 7. Supply the wording and the labels for 1 and for 7. A reader who has seen only one version must be able to answer it. It must not mention the factor, the other version, or any philosophical term of art.
3. One factual comprehension question about what the scenario explicitly states, with exactly three answer options (a, b, c) and the correct option for each version. The correct option may differ between versions if the question concerns the fact you changed.
4. A prediction of the result: its direction (A_higher, B_higher, or none) and its size (none, small, or large), as defined below.

TARGET FACTORS
- intent_accident: Intention versus accident. Whether a person brings about an outcome on purpose or by accident. What the person physically does and the outcome itself should be the same in both versions.
- doing_allowing: Doing versus allowing. Whether a person actively brings about an outcome or merely allows it to happen when they could have prevented it. The outcome, what the person knows and wants, and how easy it would have been to act differently should be the same in both versions.
- knowledge_luck: Knowledge versus lucky true belief. Whether a person's true and well-supported belief is true in the normal way or only by luck. The belief, the fact that it is true, and the evidence as the person sees it should be the same in both versions.
- moral_luck: Moral luck in outcomes. Whether one and the same choice, made with the same knowledge and the same risk, happens to turn out harmlessly or harmfully because of something outside the person's control.
- norm_causation: Norm violation and causal judgment. Whether a person's contribution to an outcome broke a rule or norm or was permitted, with their physical contribution to the outcome the same in both versions. For this factor the judgment question must ask how much that person caused the outcome, not how much they are to blame.

HOW YOUR PAIRS WILL BE TESTED
- A panel of independent readers judges your scenarios. Every reader sees only one version of a given pair, in a fresh context, with no mention of the factor or of your prediction, and answers your two questions. Readers see scenarios from many authors mixed together in random order.
- In this pilot the readers are AI language models from several model tiers, asked to give their own judgment as ordinary readers. Human readers are planned for later rounds. Write for an ordinary adult reader with no philosophy training.
- The measured result is the mean rating for version A minus the mean rating for version B, in scale points. Size is defined on its absolute value: none = below 0.5 points; small = 0.5 or more but below 1.5; large = 1.5 or more. If you predict size "none", predict direction "none", and the other way round.

SCORING
1. Prediction: did the judgments split in the direction and size you predicted? A "none" prediction is legitimate when you think the factor makes no difference, but it only counts if the two versions really do differ in the target factor.
2. Confounds: any difference between the versions other than the target factor counts against you.
3. Originality: invent your own scenarios. Re-skins of famous cases do not count: for example trolley cases, Gettier cases, Knobe's chairman, the experience machine, or any other well-known case or published experimental vignette with the names and setting changed.
4. Comprehension: the share of readers who answer your comprehension question correctly.

RULES
- Work from your own knowledge. Do not use web search, do not read or write files, and do not use any tool other than the one for returning your answer.
- Plain, concrete English. No philosophical jargon inside the scenarios or the questions.
- Be honest in your prediction: predict what you really expect the panel to do.

Return all five pairs through the structured answer, one per factor.`

const PAIR = {
  type: 'object',
  properties: {
    factor_id: { type: 'string', enum: ['intent_accident', 'doing_allowing', 'knowledge_luck', 'moral_luck', 'norm_causation'] },
    title: { type: 'string', description: 'Short neutral title for the pair (not shown to readers)' },
    version_a: { type: 'string', description: 'Scenario text, version A, at most 150 words' },
    version_b: { type: 'string', description: 'Scenario text, version B, at most 150 words' },
    intended_difference: { type: 'string', description: 'One sentence: exactly what differs between A and B' },
    judgment_question: { type: 'string', description: 'The 1-7 judgment question, identical for both versions' },
    scale_label_1: { type: 'string', description: 'Label for scale point 1' },
    scale_label_7: { type: 'string', description: 'Label for scale point 7' },
    comprehension_question: { type: 'string' },
    option_a: { type: 'string' },
    option_b: { type: 'string' },
    option_c: { type: 'string' },
    correct_option_version_a: { type: 'string', enum: ['a', 'b', 'c'] },
    correct_option_version_b: { type: 'string', enum: ['a', 'b', 'c'] },
    predicted_direction: { type: 'string', enum: ['A_higher', 'B_higher', 'none'] },
    predicted_size: { type: 'string', enum: ['none', 'small', 'large'] },
    prediction_rationale: { type: 'string', description: 'One or two sentences: why you expect this result' },
    originality_note: { type: 'string', description: 'One sentence: how this differs from known cases' },
  },
  required: ['factor_id', 'title', 'version_a', 'version_b', 'intended_difference', 'judgment_question', 'scale_label_1', 'scale_label_7', 'comprehension_question', 'option_a', 'option_b', 'option_c', 'correct_option_version_a', 'correct_option_version_b', 'predicted_direction', 'predicted_size', 'prediction_rationale', 'originality_note'],
}
const SCHEMA = {
  type: 'object',
  properties: { pairs: { type: 'array', items: PAIR, minItems: 5, maxItems: 5 } },
  required: ['pairs'],
}

const TIERS = ['haiku', 'sonnet', 'opus', 'fable']
phase('Author')
const out = await parallel(TIERS.map(t => () =>
  agent(BRIEF, { label: `author:${t}`, phase: 'Author', model: t, schema: SCHEMA })
    .then(r => ({ tier: t, result: r }))))
return out
