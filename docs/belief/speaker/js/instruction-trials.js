/**
 * Instruction Trial Data: Contains demonstration trials for instruction pages
 * These trials show specific wizard actions without requiring user responses
 */

// Instruction trial definitions 
const instructionTrialDefinitions = [
    // Demonstration 1: Signpost Demo (Wizard shows sign)
    {
        id: "instruction_signpost",
        label: "Signpost Demo",
        description: "Wizard shows a sign pointing to the gold",
        beliefIntervention: "no_belief_to_true",
        initialBelief: { state: "no_belief" },
        finalBelief: { state: "treasure_belief", goldDir: "left" },
        wizardAction: "show_signpost",
        signpostContent: { truthful: true, goldLeft: true },
        treasurePositions: { gold: "left", rocks: "right" },
        finalOutcome: "gold",
        farmerIgnoresWizard: false,
        instructionOnly: true
    },

    // Demonstration 2: Farmer Listen Demo (Farmer follows sign)
    {
        id: "instruction_listen",
        label: "Listen Demo",
        description: "Farmer follows the wizard's sign",
        beliefIntervention: "no_belief_to_true",
        initialBelief: { state: "no_belief" },
        finalBelief: { state: "treasure_belief", goldDir: "left" },
        wizardAction: "show_signpost",
        signpostContent: { truthful: true, goldLeft: true },
        treasurePositions: { gold: "left", rocks: "right" },
        finalOutcome: "gold",
        farmerIgnoresWizard: false,
        instructionOnly: true
    },

    // Demonstration 3: Farmer Ignore Demo (Farmer goes opposite to sign)
    {
        id: "instruction_ignore",
        label: "Ignore Demo",
        description: "Farmer ignores the wizard's sign",
        beliefIntervention: "false_to_false",
        initialBelief: { state: "treasure_belief", goldDir: "right" },
        finalBelief: { state: "treasure_belief", goldDir: "right" },
        wizardAction: "show_signpost",
        signpostContent: { truthful: true, goldLeft: true },
        treasurePositions: { gold: "left", rocks: "right" },
        finalOutcome: "rocks",
        farmerIgnoresWizard: true,
        instructionOnly: true
    },

    // Demonstration 4: Wizard Nothing Demo
    {
        id: "instruction_nothing",
        label: "Nothing Demo",
        description: "Wizard does nothing",
        beliefIntervention: "true_to_true_inaction",
        initialBelief: { state: "treasure_belief", goldDir: "left" },
        finalBelief: { state: "treasure_belief", goldDir: "left" },
        wizardAction: "nothing",
        signpostContent: null,
        treasurePositions: { gold: "left", rocks: "right" },
        finalOutcome: "gold",
        farmerIgnoresWizard: false,
        instructionOnly: true
    }
];

// Generate the instruction trials using the same generator as experimental trials
const instructionTrials = instructionTrialDefinitions.map(def => {
    const generator = new BeliefTrialGenerator();
    return generator.generateTrial(def);
});

// Export the data for use in instructions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { instructionTrials };
} else {
    window.InstructionTrials = { instructionTrials };
}