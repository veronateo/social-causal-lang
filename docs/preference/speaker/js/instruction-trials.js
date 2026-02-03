/**
 * Instruction Trial Data: Contains demonstration trials for instruction pages
 */

// Instruction trial definitions
const instructionTrialDefinitions = [
    // Demo 1: Wizard adds apple to LEFT (Change Right -> Left)
    {
        id: "demo_add_left",
        initialConfig: { left: { bananas: 1, apples: 0 }, right: { bananas: 0, apples: 1 } },
        initialDirection: 'right', // 1B(1) vs 1A(3) -> Goes Right
        wizardAction: { type: 'add_apple', side: 'left' }, // Adds A to Left -> 1B+1A(4) vs 1A(3) -> Switch Left
        farmerPreference: { apple: 3, banana: 1 },
        finalOutcome: 'left'
    },

    // Demo 2: Wizard adds apple to right (Change Left -> Right)
    {
        id: "demo_add_right",
        initialConfig: { left: { bananas: 1, apples: 0 }, right: { bananas: 0, apples: 1 } },
        initialDirection: 'left', // 2B(2) vs 1A(3) -> Goes Left
        wizardAction: { type: 'add_apple', side: 'right' }, // Adds A to Right -> 2B(2) vs 1A(3) -> Switch Right
        farmerPreference: { apple: 3, banana: 1 },
        finalOutcome: 'right'
    },

    // Demo 3: Wizard does nothing (Stays Right)
    {
        id: "demo_nothing",
        initialConfig: { left: { bananas: 1, apples: 0 }, right: { bananas: 0, apples: 1 } },
        initialDirection: 'right', // 2B(2) vs 1A(3) -> Goes Right
        wizardAction: { type: 'do_nothing' }, // Unchanged
        farmerPreference: { apple: 3, banana: 1 },
        finalOutcome: 'right'
    }
];

// Generate the instruction trials
const instructionTrials = instructionTrialDefinitions.map(def => {
    const generator = new PreferenceTrialGenerator();
    return generator.generateTrial(def);
});

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { instructionTrials };
} else {
    window.InstructionTrials = { instructionTrials };
}
