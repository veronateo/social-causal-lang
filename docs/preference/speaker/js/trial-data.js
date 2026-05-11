/**
 * Trial Data for Preference Intervention Experiment
 * 
 * Uses the definitions from preference-trial-definitions.js
 */

// Ensure preferenceTrialDefinitions is loaded
if (typeof preferenceTrialDefinitions === 'undefined') {
    console.error("preferenceTrialDefinitions is not defined. Make sure preference-trial-definitions.js is loaded first.");
}

const ALL_PREFERENCE_TRIALS = preferenceTrialDefinitions;

// Export if module system is used
if (typeof module !== 'undefined') module.exports = ALL_PREFERENCE_TRIALS;
