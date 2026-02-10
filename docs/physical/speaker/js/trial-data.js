/**
 * Experimental Trial Data
 */

// NOTE: This script assumes `physical-trial-generator.js` and `physical-trial-definitions.js` have been loaded first.

const generator = new TrialGenerator();
const experimentalTrials = window.TrialDefinitions.trialDefinitions.map(def => generator.generateTrial(def));

// Export the data for use in the demo controller
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { experimentalTrials };
} else {
    window.TrialData = { experimentalTrials };
}