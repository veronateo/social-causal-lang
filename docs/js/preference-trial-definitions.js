/**
 * Preference Trial Definitions
 * 
 * Defines the 14 selected scenarios for the preference intervention experiment.
 * Reduced from original 24 to balance Initial Directions (7L/7R) and include interesting cases.
 */

const preferenceTrialDefinitions = [
    // Config 1: 1B v 2A
    {
        id: 'trial_a',
        full_id: 'pref_4', // Caused (Left Init, Add Right)
        config: '1B v 2A',
        initialConfig: { left: { bananas: 1, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'left',
        wizardAction: { type: 'add_apple', side: 'right' },
        finalOutcome: 'right',
        farmerPreference: { apple: 1, banana: 2.5 },
        verb: 'Caused'
    },
    {
        id: 'trial_b',
        full_id: 'pref_7', // No Diff (Left Init, Nothing)
        config: '1B v 2A',
        initialConfig: { left: { bananas: 1, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'left',
        wizardAction: { type: 'nothing', side: 'middle' },
        finalOutcome: 'left',
        farmerPreference: { apple: 1, banana: 3 },
        verb: 'Made no difference'
    },
    {
        id: 'trial_c',
        full_id: 'pref_9', // Caused (Right Init, Add Left)
        config: '1B v 2A',
        initialConfig: { left: { bananas: 1, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'right',
        wizardAction: { type: 'add_apple', side: 'left' },
        finalOutcome: 'left',
        farmerPreference: { apple: 1, banana: 1.5 },
        verb: 'Caused'
    },
    {
        id: 'trial_d',
        full_id: 'pref_12', // No Diff (Right Init, Add Right)
        config: '1B v 2A',
        initialConfig: { left: { bananas: 1, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'right',
        wizardAction: { type: 'add_apple', side: 'right' },
        finalOutcome: 'right',
        farmerPreference: { apple: 1, banana: 1 },
        verb: 'Made no difference'
    },

    // Config 2: 2B v 1A
    {
        id: 'trial_e',
        full_id: 'pref_17', // No Diff (Left Init, Add Left)
        config: '2B v 1A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 1 } },
        initialDirection: 'left',
        wizardAction: { type: 'add_apple', side: 'left' },
        finalOutcome: 'left',
        farmerPreference: { apple: 1, banana: 1 },
        verb: 'Made no difference'
    },
    {
        id: 'trial_f',
        full_id: 'pref_20', // Caused (Left Init, Add Right)
        config: '2B v 1A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 1 } },
        initialDirection: 'left',
        wizardAction: { type: 'add_apple', side: 'right' },
        finalOutcome: 'right',
        farmerPreference: { apple: 1.5, banana: 1 },
        verb: 'Caused'
    },
    {
        id: 'trial_g',
        full_id: 'pref_25', // Caused (Right Init, Add Left)
        config: '2B v 1A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 1 } },
        initialDirection: 'right',
        wizardAction: { type: 'add_apple', side: 'left' },
        finalOutcome: 'left',
        farmerPreference: { apple: 3, banana: 1 },
        verb: 'Caused'
    },
    {
        id: 'trial_h',
        full_id: 'pref_26', // No Diff (Right Init, Add Left) [Interesting: Negative Pref]
        config: '2B v 1A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 1 } },
        initialDirection: 'right',
        wizardAction: { type: 'add_apple', side: 'left' },
        finalOutcome: 'right',
        farmerPreference: { apple: 1, banana: -2 },
        verb: 'Made no difference'
    },
    {
        id: 'trial_i',
        full_id: 'pref_32', // No Diff (Right Init, Nothing)
        config: '2B v 1A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 1 } },
        initialDirection: 'right',
        wizardAction: { type: 'nothing', side: 'middle' },
        finalOutcome: 'right',
        farmerPreference: { apple: 3, banana: 1 },
        verb: 'Made no difference'
    },

    // Config 3: 2B v 2A
    {
        id: 'trial_j',
        full_id: 'pref_33', // No Diff (Left Init, Add Left) [Balancer]
        config: '2B v 2A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'left',
        wizardAction: { type: 'add_apple', side: 'left' },
        finalOutcome: 'left',
        farmerPreference: { apple: 1, banana: 2 },
        verb: 'Made no difference'
    },
    {
        id: 'trial_k',
        full_id: 'pref_36', // Caused (Left Init, Add Right)
        config: '2B v 2A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'left',
        wizardAction: { type: 'add_apple', side: 'right' },
        finalOutcome: 'right',
        farmerPreference: { apple: 1, banana: 1.2 },
        verb: 'Caused'
    },
    {
        id: 'trial_l',
        full_id: 'pref_39', // No Diff (Left Init, Nothing)
        config: '2B v 2A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'left',
        wizardAction: { type: 'nothing', side: 'middle' },
        finalOutcome: 'left',
        farmerPreference: { apple: 1, banana: 2 },
        verb: 'Made no difference'
    },
    {
        id: 'trial_m',
        full_id: 'pref_41', // Caused (Right Init, Add Left)
        config: '2B v 2A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'right',
        wizardAction: { type: 'add_apple', side: 'left' },
        finalOutcome: 'left',
        farmerPreference: { apple: 1.5, banana: 1 },
        verb: 'Caused'
    },
    {
        id: 'trial_n',
        full_id: 'pref_48', // No Diff (Right Init, Nothing)
        config: '2B v 2A',
        initialConfig: { left: { bananas: 2, apples: 0 }, right: { bananas: 0, apples: 2 } },
        initialDirection: 'right',
        wizardAction: { type: 'nothing', side: 'middle' },
        finalOutcome: 'right',
        farmerPreference: { apple: 3, banana: 1 },
        verb: 'Made no difference'
    }
].filter(t => t.id);

if (typeof module !== 'undefined') {
    module.exports = preferenceTrialDefinitions;
}
