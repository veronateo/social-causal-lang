/**
 * Belief Trial Definitions
 */

// Create trial parameters
function createBeliefTrial(baseParams, treasureConfig) {
    const { gold, rocks } = treasureConfig;
    const suffix = gold === 'left' ? ' (left)' : ' (right)';

    return {
        ...baseParams,
        // id: baseParams.id + suffix,
        id: baseParams.id,
        label: baseParams.label + suffix,
        treasurePositions: { gold, rocks }
    };
}


// Trial type definitions

const TRIAL_TYPES = {
    // 1. No belief --> correct sign --> true belief (listens) --> gold
    trial_a: {
        id: 'trial_a',
        label: 'No belief → correct sign → true belief (listens) → gold',
        description: 'Farmer has no belief about treasure locations. Wizard shows truthful signpost. Farmer listens and gets gold.',
        beliefIntervention: 'no_belief_to_true',
        initialBelief: { state: 'no_belief' },
        wizardAction: 'show_signpost',
        signpostContent: { truthful: true },
        finalOutcome: 'gold',
        expectedVerb: ['enabled', 'caused']
    },

    // 2. No belief --> wrong sign --> false belief (listens) --> rocks
    trial_b: {
        id: 'trial_b',
        label: 'No belief → wrong sign → false belief (listens) → rocks',
        description: 'Farmer has no belief. Wizard shows deceptive signpost. Farmer listens and gets rocks.',
        beliefIntervention: 'no_belief_to_false',
        initialBelief: { state: 'no_belief' },
        wizardAction: 'show_signpost',
        signpostContent: { truthful: false },
        finalOutcome: 'rocks',
        expectedVerb: 'caused'
    },

    // 3. True belief --> wrong sign --> false belief (listens) --> rocks
    trial_c: {
        id: 'trial_c',
        label: 'True → wrong sign → false belief (listens) → rocks',
        description: 'Farmer has correct belief. Wizard shows deceptive signpost. Farmer listens and gets rocks.',
        beliefIntervention: 'true_to_false',
        wizardAction: 'show_signpost',
        signpostContent: { truthful: false },
        finalOutcome: 'rocks',
        expectedVerb: 'caused'
    },

    // 4. False belief --> correct sign --> true belief (listens) --> gold
    trial_d: {
        id: 'trial_d',
        label: 'False → correct sign → true belief (listens) → gold',
        description: 'Farmer has false belief. Wizard shows truthful signpost (correction). Farmer listens and gets gold.',
        beliefIntervention: 'false_to_true',
        wizardAction: 'show_signpost',
        signpostContent: { truthful: true },
        finalOutcome: 'gold',
        expectedVerb: ['caused', 'enabled', 'allowed']
    },

    // 5. True belief --> correct sign (reinforces) --> true belief (same) --> gold
    trial_e: {
        id: 'trial_e',
        label: 'True → correct sign (reinforces) → true belief (same) → gold',
        description: 'Farmer has correct belief. Wizard confirms with truthful signpost. Farmer gets gold.',
        beliefIntervention: 'true_to_true_reinforce',
        wizardAction: 'show_signpost',
        signpostContent: { truthful: true },
        finalOutcome: 'gold',
        expectedVerb: 'made_no_difference'
    },

    // 6. False belief --> wrong sign (reinforces) --> false belief (same) --> rocks
    trial_f: {
        id: 'trial_f',
        label: 'False → wrong sign (reinforces) → false belief (same) → rocks',
        description: 'Farmer has false belief. Wizard reinforces with deceptive signpost. Farmer gets rocks.',
        beliefIntervention: 'false_to_false_reinforce',
        wizardAction: 'show_signpost',
        signpostContent: { truthful: false },
        finalOutcome: 'rocks',
        expectedVerb: ['caused', 'made_no_difference']
    },

    // 7. True belief --> nothing --> true belief (same) --> gold
    trial_g: {
        id: 'trial_g',
        label: 'True → nothing → true belief (same) → gold',
        description: 'Farmer has correct belief. Wizard does nothing. Farmer gets gold.',
        beliefIntervention: 'true_to_true_inaction',
        wizardAction: 'nothing',
        signpostContent: null,
        finalOutcome: 'gold',
        expectedVerb: ['allowed', 'made_no_difference']
    },

    // 8. False belief --> nothing --> false belief (same) --> rocks
    trial_h: {
        id: 'trial_h',
        label: 'False → nothing → false belief (same) → rocks',
        description: 'Farmer has false belief. Wizard does nothing (does not correct). Farmer gets rocks.',
        beliefIntervention: 'false_to_false_inaction',
        wizardAction: 'nothing',
        signpostContent: null,
        finalOutcome: 'rocks',
        expectedVerb: ['allowed', 'caused', 'made_no_difference']
    },

    // 9. True belief --> wrong sign --> true belief (ignores) --> gold
    trial_i: {
        id: 'trial_i',
        label: 'True → wrong sign → true belief (ignores) → gold',
        description: 'Farmer has correct belief. Wizard shows deceptive signpost. Farmer ignores wizard and keeps true belief. Gets gold.',
        beliefIntervention: 'true_to_false_ignore',
        wizardAction: 'show_signpost',
        signpostContent: { truthful: false },
        farmerIgnoresWizard: true,
        finalOutcome: 'gold',
        expectedVerb: 'made_no_difference'
    },

    // 10. False belief --> correct sign --> false belief (ignores) --> rocks
    trial_j: {
        id: 'trial_j',
        label: 'False → correct sign → false belief (ignores) → rocks',
        description: 'Farmer has false belief. Wizard shows truthful signpost (correction). Farmer ignores wizard and keeps false belief. Gets rocks.',
        beliefIntervention: 'false_to_true_ignore',
        wizardAction: 'show_signpost',
        signpostContent: { truthful: true },
        farmerIgnoresWizard: true,
        finalOutcome: 'rocks',
        expectedVerb: 'made_no_difference'
    },

    // 11. No belief --> nothing --> guess gold --> gold
    trial_k: {
        id: 'trial_k',
        label: 'No belief → nothing → guess gold → gold',
        description: 'Farmer has no belief. Wizard does nothing. Farmer guesses correctly and gets gold.',
        beliefIntervention: 'no_belief_to_gold_inaction',
        wizardAction: 'nothing',
        signpostContent: null,
        finalOutcome: 'gold',
        expectedVerb: ['allowed', 'made_no_difference', 'enabled']
    },

    // 12. No belief --> nothing --> guess rocks --> rocks
    trial_l: {
        id: 'trial_l',
        label: 'No belief → nothing → guess rocks → rocks',
        description: 'Farmer has no belief. Wizard does nothing. Farmer guesses incorrectly and gets rocks.',
        beliefIntervention: 'no_belief_to_rocks_inaction',
        wizardAction: 'nothing',
        signpostContent: null,
        finalOutcome: 'rocks',
        expectedVerb: ['allowed', 'made_no_difference']
    },

    // 13. No belief --> correct sign --> ignore / do opposite --> rocks
    trial_m: {
        id: 'trial_m',
        label: 'No belief → correct sign → ignore → rocks',
        description: 'Farmer has no belief. Wizard shows truthful sign. Farmer ignores/does opposite and gets rocks.',
        beliefIntervention: 'no_belief_to_true_ignore',
        wizardAction: 'show_signpost',
        signpostContent: { truthful: true },
        farmerIgnoresWizard: true,
        finalOutcome: 'rocks',
        expectedVerb: ['caused', 'made_no_difference']
    },

    // 14. No belief --> wrong sign --> ignore / do opposite --> gold
    trial_n: {
        id: 'trial_n',
        label: 'No belief → wrong sign → ignore → gold',
        description: 'Farmer has no belief. Wizard shows deceptive sign. Farmer ignores/does opposite and gets gold.',
        beliefIntervention: 'no_belief_to_false_ignore',
        wizardAction: 'show_signpost',
        signpostContent: { truthful: false },
        farmerIgnoresWizard: true,
        finalOutcome: 'gold',
        expectedVerb: ['caused', 'made_no_difference']
    }
};

// Generate full trial set

/**
 * Generates complete trial parameters for each intervention type with counterbalanced treasure positions
 */
function generateAllTrials() {
    const allTrials = [];
    const trialTypes = Object.values(TRIAL_TYPES);

    // Configuration to ensure 50/50 Farmer Movement Balance (7 Right, 7 Left).
    // This assignment results in 6 trials with Gold Right and 8 with Gold Left.
    const GOLD_RIGHT_CONFIG = {
        'trial_a': true,          // Outcome Gold -> Move Right
        'trial_b': true,          // Outcome Rocks (L) -> Move Left
        'trial_c': false,         // Outcome Rocks (R) -> Move Right
        'trial_d': false,         // Outcome Gold -> Move Left
        'trial_e': true,          // Outcome Gold -> Move Right
        'trial_f': false,         // Outcome Rocks (R) -> Move Right
        'trial_g': true,          // Outcome Gold -> Move Right
        'trial_h': false,         // Outcome Rocks (R) -> Move Right
        'trial_i': true,          // Outcome Gold -> Move Right
        'trial_j': true,          // Outcome Rocks (L) -> Move Left
        'trial_k': false,         // Outcome Gold -> Move Left
        'trial_l': true,          // Outcome Rocks (L) -> Move Left
        'trial_m': true,          // Outcome Rocks (L) -> Move Left
        'trial_n': false          // Outcome Gold -> Move Left
    };

    trialTypes.forEach(trialType => {
        const isGoldRight = GOLD_RIGHT_CONFIG[trialType.id];
        const goldPos = isGoldRight ? 'right' : 'left';
        const rocksPos = isGoldRight ? 'left' : 'right';

        const trial = createBeliefTrial(trialType, { gold: goldPos, rocks: rocksPos });

        trial.initialBelief = getInitialBelief(trialType.beliefIntervention, { gold: goldPos });
        trial.finalBelief = getFinalBelief(trialType.beliefIntervention, { gold: goldPos });

        if (trial.signpostContent) {
            const isTruthful = trial.signpostContent.truthful;
            const goldLeft = goldPos === 'left';
            const signPointsLeft = goldLeft ? isTruthful : !isTruthful;

            trial.signpostContent = {
                ...trial.signpostContent,
                goldLeft: signPointsLeft
            };
        }
        allTrials.push(trial);
    });

    return allTrials;
}

/**
 * Helper: Get initial belief state based on intervention type and treasure positions
 */
function getInitialBelief(interventionType, treasurePositions) {
    const { gold } = treasurePositions;

    switch (interventionType) {
        case 'no_belief_to_true':
        case 'no_belief_to_false':
        case 'no_belief_to_gold_inaction':
        case 'no_belief_to_rocks_inaction':
        case 'no_belief_to_true_ignore':
        case 'no_belief_to_false_ignore':
            return { state: 'no_belief' };

        case 'true_to_false':
        case 'true_to_false_ignore':
        case 'true_to_true_reinforce':
        case 'true_to_true_inaction':
            // True belief: farmer correctly believes where gold is
            return {
                state: 'treasure_belief',
                goldDir: gold
            };

        case 'false_to_true':
        case 'false_to_true_ignore':
        case 'false_to_false_reinforce':
        case 'false_to_false_inaction':
            // False belief: farmer incorrectly believes opposite of reality
            return {
                state: 'treasure_belief',
                goldDir: gold === 'left' ? 'right' : 'left'
            };

        default:
            return { state: 'no_belief' };
    }
}

/**
 * Helper: Get final belief state based on intervention type and treasure positions
 */
function getFinalBelief(interventionType, treasurePositions) {
    const { gold } = treasurePositions;

    switch (interventionType) {
        case 'no_belief_to_true':
        case 'false_to_true':
        case 'true_to_true_reinforce':
        case 'true_to_true_inaction':
        case 'no_belief_to_gold_inaction':
        case 'no_belief_to_false_ignore':
            // Final belief is true
            return {
                state: 'treasure_belief',
                goldDir: gold
            };

        case 'no_belief_to_false':
        case 'true_to_false':
        case 'false_to_false_reinforce':
        case 'false_to_false_inaction':
        case 'no_belief_to_rocks_inaction':
        case 'no_belief_to_true_ignore':
            // Final belief is false
            return {
                state: 'treasure_belief',
                goldDir: gold === 'left' ? 'right' : 'left'
            };

        case 'true_to_false_ignore':
            // Farmer ignores deceptive signpost, keeps true belief
            return {
                state: 'treasure_belief',
                goldDir: gold
            };

        case 'false_to_true_ignore':
            // Farmer ignores correction signpost, keeps false belief
            return {
                state: 'treasure_belief',
                goldDir: gold === 'left' ? 'right' : 'left'
            };

        default:
            return { state: 'no_belief' };
    }
}


const ALL_BELIEF_TRIALS = generateAllTrials();

// Export for use in experiments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        TRIAL_TYPES,
        ALL_BELIEF_TRIALS,
        generateAllTrials
    };
}
