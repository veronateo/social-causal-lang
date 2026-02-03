const listenerTrials = [
    {
        "trial_number": 0,
        "verb": "enabled",
        "outcome": "apple",
        "utterance": "The wizard enabled the farmer to get the apple.",
        "scenario1_animation": "trial_j",
        "scenario2_animation": "trial_c",
        "modal_animation": "trial_c",
        "modal_position": "scenario2"
    },
    {
        "trial_number": 1,
        "verb": "enabled",
        "outcome": "apple",
        "utterance": "The wizard enabled the farmer to get the apple.",
        "scenario1_animation": "trial_c",
        "scenario2_animation": "trial_i",
        "modal_animation": "trial_c",
        "modal_position": "scenario1"
    },
    {
        "trial_number": 2,
        "verb": "made_no_difference",
        "outcome": "banana",
        "utterance": "The wizard made no difference to the farmer getting the banana.",
        "scenario1_animation": "trial_d",
        "scenario2_animation": "trial_b",
        "modal_animation": "trial_b",
        "modal_position": "scenario2"
    },
    {
        "trial_number": 3,
        "verb": "caused",
        "outcome": "banana",
        "utterance": "The wizard caused the farmer to get the banana.",
        "scenario1_animation": "trial_a",
        "scenario2_animation": "trial_d",
        "modal_animation": "trial_a",
        "modal_position": "scenario1"
    },
    {
        "trial_number": 4,
        "verb": "allowed",
        "outcome": "apple",
        "utterance": "The wizard allowed the farmer to get the apple.",
        "scenario1_animation": "trial_e",
        "scenario2_animation": "trial_j",
        "modal_animation": "trial_j",
        "modal_position": "scenario2"
    },
    {
        "trial_number": 5,
        "verb": "made_no_difference",
        "outcome": "banana",
        "utterance": "The wizard made no difference to the farmer getting the banana.",
        "scenario1_animation": "trial_f",
        "scenario2_animation": "trial_h",
        "modal_animation": "trial_f",
        "modal_position": "scenario1"
    },
    {
        "trial_number": 6,
        "verb": "made_no_difference",
        "outcome": "banana",
        "utterance": "The wizard made no difference to the farmer getting the banana.",
        "scenario1_animation": "trial_d",
        "scenario2_animation": "trial_g",
        "modal_animation": "trial_d",
        "modal_position": "scenario1"
    },
    {
        "trial_number": 7,
        "verb": "enabled",
        "outcome": "apple",
        "utterance": "The wizard enabled the farmer to get the apple.",
        "scenario1_animation": "trial_c",
        "scenario2_animation": "trial_e",
        "modal_animation": "trial_c",
        "modal_position": "scenario1"
    },
    {
        "trial_number": 8,
        "verb": "allowed",
        "outcome": "apple",
        "utterance": "The wizard allowed the farmer to get the apple.",
        "scenario1_animation": "trial_i",
        "scenario2_animation": "trial_e",
        "modal_animation": "trial_e",
        "modal_position": "scenario2"
    },
    {
        "trial_number": 9,
        "verb": "caused",
        "outcome": "banana",
        "utterance": "The wizard caused the farmer to get the banana.",
        "scenario1_animation": "trial_h",
        "scenario2_animation": "trial_b",
        "modal_animation": "trial_h",
        "modal_position": "scenario1"
    },
    {
        "trial_number": 10,
        "verb": "allowed",
        "outcome": "apple",
        "utterance": "The wizard allowed the farmer to get the apple.",
        "scenario1_animation": "trial_i",
        "scenario2_animation": "trial_j",
        "modal_animation": "trial_i",
        "modal_position": "scenario1"
    },
    {
        "trial_number": 11,
        "verb": "caused",
        "outcome": "banana",
        "utterance": "The wizard caused the farmer to get the banana.",
        "scenario1_animation": "trial_h",
        "scenario2_animation": "trial_a",
        "modal_animation": "trial_a",
        "modal_position": "scenario2"
    }
];
    
    // Export for use in experiment
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { listenerTrials };
    } else {
        window.ListenerTrialData = { listenerTrials };
    }
    