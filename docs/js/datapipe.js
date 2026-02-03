/**
 * DataPipe integration using jsPsych plugin
 */

let prolific_id;
try {
    // For jsPsych v7+
    prolific_id = jsPsych.data.getURLVariable('PROLIFIC_PID');
} catch (error) {
    // Fallback: manually parse URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    prolific_id = urlParams.get('PROLIFIC_PID');
}

// Fallback if Prolific ID is not available
if (!prolific_id || prolific_id === null || prolific_id === undefined || prolific_id === '') {
    console.warn('[DataPipe] No Prolific ID found in URL, generating fallback ID');
    prolific_id = 'unknown_' + Math.random().toString(36).substr(2, 9);
} else {
    console.log('[DataPipe] Using Prolific ID:', prolific_id);
}

const filename = `${prolific_id}.csv`;

// Detect which experiment is running based on URL path
const path = window.location.pathname;

// Experiment IDs
const BELIEF_SPEAKER_ID = "MYVLIgu7dTx7";
const PREFERENCE_SPEAKER_ID = "C3k8Hkurc6Ba";
const PHYSICAL_LISTENER_ID = "KOsAhuOTX8Am";
const PHYSICAL_SPEAKER_ID = "AqdxpB7wOgK5";

let experiment_id;
let isListenerExperiment = false;

if (path.includes('/belief/speaker')) {
    experiment_id = BELIEF_SPEAKER_ID;
    // console.log('[DataPipe] Mode: Belief Speaker');
} else if (path.includes('/preference/speaker')) {
    experiment_id = PREFERENCE_SPEAKER_ID;
    // console.log('[DataPipe] Mode: Preference Speaker');
} else if (path.includes('/physical/listener') || path.includes('/physical/listeners')) {
    experiment_id = PHYSICAL_LISTENER_ID;
    isListenerExperiment = true;
    // console.log('[DataPipe] Mode: Physical Listener');
} else if (path.includes('/physical/speaker')) {
    experiment_id = PHYSICAL_SPEAKER_ID;
    // console.log('[DataPipe] Mode: Physical Speaker');
} else {
    console.warn('[DataPipe] Path does not match known experiments. Defaulting to Physical Speaker.');
    experiment_id = PHYSICAL_SPEAKER_ID;
}

// Save trials (handles both speaker and listener experiments)
const save_trials = {
    type: jsPsychPipe,
    action: "save",
    experiment_id: experiment_id,
    filename: `${prolific_id}_trials.csv`,
    data_string: () => {
        if (experiment_id === BELIEF_SPEAKER_ID) {
            // Belief Speaker experiment
            const trialData = jsPsych.data.get().filter({ trial_type: 'belief-gridworld-trial' });
            let csv = 'trial_id,response,rt\n';
            const trials = trialData.values();

            for (let trial of trials) {
                // trial.trial_params.id will be like "trial_a"
                csv += `${escapeCSV(trial.trial_id)},${escapeCSV(trial.response)},${escapeCSV(trial.rt)}\n`;
            }
            return csv;

        } else if (experiment_id === PREFERENCE_SPEAKER_ID) {
            // Preference Speaker experiment
            const trialData = jsPsych.data.get().filter({ trial_type: 'preference-gridworld-trial' });
            let csv = 'trial_id,response,rt\n';
            const trials = trialData.values();

            for (let trial of trials) {
                csv += `${escapeCSV(trial.trial_id)},${escapeCSV(trial.response)},${escapeCSV(trial.rt)}\n`;
            }
            return csv;

        } else if (isListenerExperiment) {
            // Listener experiment: save both speaker and listener trials
            const speakerData = jsPsych.data.get().filter({ trial_type: 'gridworld-trial' });
            const listenerData = jsPsych.data.get().filter({ trial_type: 'listener-trial' });

            // Create CSV header
            let csv = 'task,trial_id,response,rt\n';

            // Add speaker trials
            const speakerTrials = speakerData.values();
            for (let trial of speakerTrials) {
                csv += `${escapeCSV(trial.task)},${escapeCSV(trial.trial_id)},${escapeCSV(trial.response)},${escapeCSV(trial.rt)}\n`;
            }

            // Add listener trials 
            const listenerTrials = listenerData.values();
            for (let trial of listenerTrials) {
                csv += `${escapeCSV(trial.task)},${escapeCSV(trial.trial_number)},${escapeCSV(trial.response)},${escapeCSV(trial.rt)}\n`;
            }

            return csv;
        } else {
            // Physical Speaker experiment (default)
            const trialData = jsPsych.data.get().filter({ trial_type: 'gridworld-trial' });
            let csv = 'trial_id,response,rt\n';
            const trials = trialData.values();

            for (let trial of trials) {
                csv += `${escapeCSV(trial.trial_id)},${escapeCSV(trial.response)},${escapeCSV(trial.rt)}\n`;
            }
            return csv;
        }
    }
};


function escapeCSV(value) {
    if (value === null || value === undefined) {
        return '';
    }

    const str = String(value);

    if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
        return '"' + str.replace(/"/g, '""') + '"';
    }

    return str;
}

// Save demographic survey
const save_demographics = {
    type: jsPsychPipe,
    action: "save",
    experiment_id: experiment_id,
    filename: `${prolific_id}_feedback.csv`,
    data_string: () => {
        const demographicData = jsPsych.data.get().filter({ trial_type: 'survey-html-form' }).last(1);
        // Create CSV with separate columns for demographic data
        let csv = 'age,gender,race,ethnicity,factors,feedback,rt\n';
        const demo = demographicData.values()[0];
        const response = demo.response;
        csv += `${escapeCSV(response.age)},${escapeCSV(response.gender)},${escapeCSV(response.race)},${escapeCSV(response.ethnicity)},${escapeCSV(response.factors)},${escapeCSV(response.feedback)},${escapeCSV(demo.rt)}\n`;

        return csv;
    }
};

// Export for use in experiment.js
window.DataPipeSave = {
    save_trials: save_trials,
    save_demographics: save_demographics,
    filename: filename,
    prolific_id: prolific_id
};
