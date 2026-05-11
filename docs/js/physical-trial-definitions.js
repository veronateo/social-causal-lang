/**
 * Shared Trial Definitions
 * Used by both speaker and listener experiments
 */

const trialDefinitions = [
    // Trial (a): farmer → apple, wizard places rock, farmer reaches banana
    // Caused
    {
        id: "trial_a",
        label: "Trial (a)",
        description: "Farmer goes to apple, wizard places rock, farmer reaches banana",
        initialDirectionGoal: "apple",
        wizardAction: "place_rock",
        rockStartsPresent: false,
        finalOutcome: "banana",
    },
    // Trial (b): farmer → banana, wizard places rock, farmer reaches banana
    // Made no difference
    {
        id: "trial_b",
        label: "Trial (b)",
        description: "Farmer goes to banana, wizard places rock, farmer reaches banana",
        initialDirectionGoal: "banana",
        wizardAction: "place_rock",
        rockStartsPresent: false,
        finalOutcome: "banana",
    },
    // Trial (c): rock initially present, farmer → banana, wizard removes rock, farmer reaches apple
    // Enabled
    {
        id: "trial_c",
        label: "Trial (c)",
        description: "Rock initially present, farmer goes to banana, wizard removes rock, farmer reaches apple",
        initialDirectionGoal: "banana",
        wizardAction: "remove_rock",
        rockStartsPresent: true,
        finalOutcome: "apple",
    },
    // Trial (d): rock initially present, farmer → banana, wizard removes rock, farmer reaches banana
    // Made no difference
    {
        id: "trial_d",
        label: "Trial (d)",
        description: "Rock initially present, farmer goes to banana, wizard removes rock, farmer reaches banana",
        initialDirectionGoal: "banana",
        wizardAction: "remove_rock",
        rockStartsPresent: true,
        finalOutcome: "banana",
    },
    // Trial (e): farmer → apple, wizard does nothing, farmer reaches apple
    // Allowed
    {
        id: "trial_e",
        label: "Trial (e)",
        description: "Farmer goes to apple, wizard does nothing, farmer reaches apple",
        initialDirectionGoal: "apple",
        wizardAction: "nothing",
        rockStartsPresent: false,
        finalOutcome: "apple",
    },
    // Trial (f): farmer → banana, wizard does nothing, farmer reaches banana
    // Made no difference
    {
        id: "trial_f",
        label: "Trial (f)",
        description: "Farmer goes to banana, wizard does nothing, farmer reaches banana",
        initialDirectionGoal: "banana",
        wizardAction: "nothing",
        rockStartsPresent: false,
        finalOutcome: "banana",
    },
    // Trial (g): rock initially present, farmer → banana, wizard does nothing, farmer reaches banana
    // Made no difference
    {
        id: "trial_g",
        label: "Trial (g)",
        description: "Rock initially present, farmer goes to banana, wizard does nothing, farmer reaches banana",
        initialDirectionGoal: "banana",
        wizardAction: "nothing",
        rockStartsPresent: true,
        finalOutcome: "banana",
    },
    // Trial (h): rock initially present, farmer → apple, wizard does nothing, farmer reaches banana
    // Caused
    {
        id: "trial_h",
        label: "Trial (h)",
        description: "Rock initially present, farmer goes to apple hoping wizard removes rock, but wizard does nothing, farmer reaches banana",
        initialDirectionGoal: "apple",
        wizardAction: "nothing",
        rockStartsPresent: true,
        finalOutcome: "banana",
    },
    // Trial (i): rock initially present, farmer → apple, wizard removes rock, farmer reaches apple
    // Enabled
    {
        id: "trial_i",
        label: "Trial (i)",
        description: "Rock initially present, farmer goes to apple, wizard removes rock, farmer reaches apple",
        initialDirectionGoal: "apple",
        wizardAction: "remove_rock",
        rockStartsPresent: true,
        finalOutcome: "apple",
    },
    // Trial (j): farmer → banana, wizard does nothing, farmer reaches apple
    // Allowed
    {
        id: "trial_j",
        label: "Trial (j)",
        description: "Farmer goes to banana, wizard does nothing, farmer reaches apple",
        initialDirectionGoal: "banana",
        wizardAction: "nothing",
        rockStartsPresent: false,
        finalOutcome: "apple",
    }
];

// Create a lookup map by trial ID
const trialDefinitionsMap = {};
trialDefinitions.forEach(def => {
    trialDefinitionsMap[def.id] = def;
});

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { trialDefinitions, trialDefinitionsMap };
} else {
    window.TrialDefinitions = { trialDefinitions, trialDefinitionsMap };
}
