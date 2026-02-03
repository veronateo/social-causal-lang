/**
 * Instruction Trial Data: Contains demonstration trials for instruction pages
 * These trials show specific wizard actions without requiring user responses
 */

// Instruction trial definitions 
const instructionTrialDefinitions = [
    // Demonstration: Wizard placing a rock
    {
        id: "instruction_place_rock",
        label: "Place Rock Demo",
        description: "Wizard places a rock to demonstrate the action",
        initialDirectionGoal: "apple", // Farmer wants apple but won't move
        wizardAction: "place_rock",
        rockStartsPresent: false,
        finalOutcome: "apple", // Farmer stays put, doesn't actually move
        instructionOnly: true // Flag to indicate this is for instruction purposes
    },
    
    // Demonstration: Wizard removing a rock
    {
        id: "instruction_remove_rock", 
        label: "Remove Rock Demo",
        description: "Wizard removes a rock to demonstrate the action",
        initialDirectionGoal: "banana", // Farmer wants banana but won't move
        wizardAction: "remove_rock",
        rockStartsPresent: true, // Rock is initially present
        finalOutcome: "banana", // Farmer stays put, doesn't actually move
        instructionOnly: true // Flag to indicate this is for instruction purposes
    },
    
    // Demonstration: Wizard doing nothing
    {
        id: "instruction_wizard_nothing",
        label: "Wizard Nothing Demo", 
        description: "Wizard waves wand but does nothing to demonstrate the action",
        initialDirectionGoal: "apple", // Farmer wants apple but won't move
        wizardAction: "nothing",
        rockStartsPresent: false,
        finalOutcome: "apple", // Farmer stays put, doesn't actually move
        instructionOnly: true // Flag to indicate this is for instruction purposes
    }
];

// Generate the instruction trials using the same generator as experimental trials
const instructionTrials = instructionTrialDefinitions.map(def => {
    const generator = new TrialGenerator();
    return generator.generateTrial(def);
});

// Export the data for use in instructions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { instructionTrials };
} else {
    window.InstructionTrials = { instructionTrials };
} 