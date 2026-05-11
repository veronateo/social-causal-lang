/**
 * preference/speaker/js/experiment.js
 * 
 * Main experiment logic for the Preference Speaker Experiment.
 */

const jsPsych = initJsPsych({
    show_progress_bar: true,
    message_progress_bar: 'Completion Progress',
    on_finish: function () {
        // Redirect to Prolific completion URL
        const prolific_completion_url = "https://app.prolific.com/submissions/complete?cc=CNYPV5QR";
        window.location.href = prolific_completion_url;
    },
    override_safe_mode: true
});

/**
 * Custom jsPsych plugin for the preference grid world trial.
 */
class PreferenceGridworldTrialPlugin {
    constructor(jsPsych) {
        this.jsPsych = jsPsych;
    }

    static info = {
        name: 'preference-gridworld-trial',
        parameters: {
            trial_params: {
                type: 'object',
                pretty_name: 'Trial Parameters',
                default: undefined,
                description: 'The trial parameters from trial-data.js'
            },
            demo_mode: {
                type: 'boolean',
                pretty_name: 'Demo Mode',
                default: false,
                description: 'If true, auto-plays animation and hides question'
            }
        }
    };

    trial(display_element, trial) {
        const isDemo = trial.demo_mode || false;
        const generator = new PreferenceTrialGenerator();
        const trialData = generator.generateTrial(trial.trial_params);

        let html = `
            <div class="gw-container">
                <div class="gw-stimulus">
                    <p class="gw-prompt">${isDemo ? '' : 'Click "Play Animation" to see what happened.'}</p>
                    <canvas id="gridCanvas" class="gw-canvas"></canvas>`;

        if (!isDemo) {
            html += `
                    <div class="gw-buttons">
                        <button id="playBtn" class="jspsych-btn">Play Animation</button>
                        <button id="replayBtn" class="jspsych-btn" style="display: none;">Replay Animation</button>
                    </div>`;
        } else {
            html += `
                    <div class="gw-buttons" style="margin-top: 15px;">
                        <button id="continueBtn" class="jspsych-btn" disabled>Continue</button>
                    </div>`;
        }

        html += `
                </div>`;

        if (!isDemo) {
            html += `
                <div id="gw-question-container" class="gw-question-container" style="visibility: hidden; margin-top: 50px; text-align: left; width: fit-content; margin-left: auto; margin-right: auto;">
                    <h3>Which sentence best describes what happened?</h3>
                    <form id="gw-form">
                        <div class="gw-option" style="margin-bottom: 10px;">
                            <input type="radio" name="causalQuestion" id="opt1" value="caused" required>
                            <label for="opt1">The wizard <strong>caused</strong> the farmer to get the ${trial.trial_params.finalOutcome} basket.</label>
                        </div>
                        <div class="gw-option" style="margin-bottom: 10px;">
                            <input type="radio" name="causalQuestion" id="opt2" value="enabled" required>
                            <label for="opt2">The wizard <strong>enabled</strong> the farmer to get the ${trial.trial_params.finalOutcome} basket.</label>
                        </div>
                        <div class="gw-option" style="margin-bottom: 10px;">
                            <input type="radio" name="causalQuestion" id="opt3" value="allowed" required>
                            <label for="opt3">The wizard <strong>allowed</strong> the farmer to get the ${trial.trial_params.finalOutcome} basket.</label>
                        </div>
                        <div class="gw-option" style="margin-bottom: 10px;">
                            <input type="radio" name="causalQuestion" id="opt4" value="made_no_difference" required>
                            <label for="opt4">The wizard <strong>made no difference</strong> to the farmer getting the ${trial.trial_params.finalOutcome} basket.</label>
                        </div>
                        <button type="submit" id="submitBtn" class="jspsych-btn btn-blue" style="margin-top: 20px; margin-bottom: 40px; display: block; margin-left: auto; margin-right: auto;" disabled>Submit</button>
                    </form>
                </div>`;
        }

        html += `</div>`;
        display_element.innerHTML = html;
        const startTime = performance.now();

        const canvas = document.getElementById('gridCanvas');
        const renderer = new PreferenceGridWorldRenderer(canvas, {
            imageBasePath: '../../images',
            horizontalBorder: 80
        });

        const imageTypes = [
            'farmer', 'wizard', 'wizard-wand', 'lightning',
            'thought', 'thought-middle',
            'one-apple-basket', 'two-apple-basket', 'three-apple-basket',
            'one-banana-basket', 'two-banana-basket',
            'one-apple-one-banana-basket', 'two-banana-one-apple-basket', 'two-apple-one-banana-basket',
            'empty-basket', 'add-apple'
        ];

        const imagePromises = imageTypes.map(type => new Promise(resolve => {
            const img = new Image();
            img.onload = () => {
                renderer.images.set(type, img);
                resolve();
            };
            img.onerror = () => {
                console.warn(`Failed to load image: ../../images/${type}.png`);
                resolve();
            };
            img.src = `../../images/${type}.png`;
        }));

        Promise.all(imagePromises).then(() => {
            renderer.renderFrame(trialData, 0);
        });

        if (isDemo) {
            setTimeout(() => {
                let firstAnimationComplete = false;
                renderer.playAnimation(trialData, {
                    loop: true,
                    speed: 700,
                    onFrameChange: (frameIndex) => {
                        if (!firstAnimationComplete && frameIndex === trialData.frames.length - 1) {
                            firstAnimationComplete = true;
                            setTimeout(() => {
                                const continueBtn = document.getElementById('continueBtn');
                                if (continueBtn) continueBtn.disabled = false;
                            }, 500);
                        }
                    }
                });
            }, 1000);

            const continueBtn = document.getElementById('continueBtn');
            if (continueBtn) {
                continueBtn.addEventListener('click', () => {
                    renderer.stopAnimation();
                    display_element.innerHTML = '';
                    this.jsPsych.finishTrial({ demo: true });
                });
            }
        } else {
            const playBtn = document.getElementById('playBtn');
            const replayBtn = document.getElementById('replayBtn');
            const submitBtn = document.getElementById('submitBtn');
            const radioButtons = display_element.querySelectorAll('input[name="causalQuestion"]');
            const prompt = document.querySelector('.gw-prompt');

            const playAnimation = (isReplay = false) => {
                replayBtn.disabled = true;
                if (!isReplay) playBtn.disabled = true;

                // Immediately show initial state
                renderer.renderFrame(trialData, 0);

                setTimeout(() => {
                    renderer.playAnimation(trialData, {
                        loop: false,
                        speed: 800,
                        onComplete: () => {
                            if (!isReplay) {
                                playBtn.style.display = 'none';
                                replayBtn.style.display = 'inline-block';
                                document.getElementById('gw-question-container').style.visibility = 'visible';
                            }
                            replayBtn.disabled = false;
                            prompt.innerText = 'Please answer the question below.';
                        }
                    });
                }, 2000);
            };

            playBtn.addEventListener('click', () => playAnimation(false));
            replayBtn.addEventListener('click', () => playAnimation(true));

            radioButtons.forEach(radio => {
                radio.addEventListener('change', () => {
                    submitBtn.disabled = false;
                });
            });

            document.getElementById('gw-form').addEventListener('submit', (e) => {
                e.preventDefault();
                const trial_data_to_save = {
                    trial_id: trial.trial_params.id,
                    config: trial.trial_params.config,
                    response: document.querySelector('input[name="causalQuestion"]:checked').value,
                    rt: Math.round(performance.now() - startTime),
                    intervention: trial.trial_params.wizardAction.type === 'do_nothing' ? 'nothing' : 'intervention',
                    outcome: trial.trial_params.finalOutcome,
                };

                display_element.innerHTML = '';
                this.jsPsych.finishTrial(trial_data_to_save);
            });
        }
    }
}

let timeline = [];

// Preload Images
timeline.push({
    type: jsPsychPreload,
    images: [
        '../../images/farmer.png', '../../images/wizard.png', '../../images/wizard-wand.png',
        '../../images/lightning.png', '../../images/thought.png', '../../images/thought-middle.png',
        '../../images/apple.png', '../../images/banana.png',
        '../../images/one-apple-basket.png', '../../images/two-apple-basket.png', '../../images/three-apple-basket.png',
        '../../images/one-banana-basket.png', '../../images/two-banana-basket.png',
        '../../images/one-apple-one-banana-basket.png', '../../images/two-banana-one-apple-basket.png', '../../images/two-apple-one-banana-basket.png',
        '../../images/empty-basket.png',
        '../../images/add-apple.png'
    ]
});

// Consent
timeline.push({
    ...consent,
    on_finish: function (data) {
        if (consent.on_finish) consent.on_finish(data);
        jsPsych.setProgressBar(0.10);
    }
});

// Attention Check
const attention_check = {
    type: jsPsychSurveyHtmlForm,
    preamble: '<h3>Comprehension Check</h3><p>Please answer the following questions to continue.</p>',
    html: `
        <div class="jspsych-content" style="max-width: 700px; text-align: left;">
            <p style="font-weight: bold; margin-bottom: 1em;">1. How many times can the wizard act? <span style="color: red;">*</span></p>
            <div style="padding-left: 2em;"> 
                <p><input type="radio" name="wizard_actions" value="1" required> 1</p>
                <p><input type="radio" name="wizard_actions" value="2" required> 2</p>
                <p><input type="radio" name="wizard_actions" value="3" required> 3</p>
            </div>
            <p style="margin-top: 2em; font-weight: bold; margin-bottom: 1em;">2. What can the wizard do? (select all that apply) <span style="color: red;">*</span></p>
            <div style="padding-left: 2em;">
                <p><input type="checkbox" name="wizard_rain" value="Make it rain"> Make it rain</p>
                <p><input type="checkbox" name="wizard_apple" value="Add an apple"> Add an apple</p>
                <p><input type="checkbox" name="wizard_banana" value="Add a banana"> Add a banana</p>
                <p><input type="checkbox" name="wizard_nothing" value="Do nothing"> Do nothing</p>
            </div>
        </div>
    `,
    button_label: 'Submit',
    on_load: function () {
        // Enable/disable submit button validation logic
        const submitButton = document.querySelector('#jspsych-survey-html-form-next');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.style.opacity = '0.5';

            const checkFormValidity = () => {
                const radioButton = document.querySelector('input[name="wizard_actions"]:checked');
                const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');

                if (radioButton && checkboxes.length > 0) {
                    submitButton.disabled = false;
                    submitButton.style.opacity = '1';
                } else {
                    submitButton.disabled = true;
                    submitButton.style.opacity = '0.5';
                }
            };

            const inputs = document.querySelectorAll('input');
            inputs.forEach(input => input.addEventListener('change', checkFormValidity));
        }
    },
    on_finish: function (data) {
        const correct_farmer = data.response.wizard_actions === '1';
        const correct_wizard =
            !data.response.wizard_rain &&
            data.response.wizard_apple &&
            !data.response.wizard_banana &&
            data.response.wizard_nothing;

        data.correct = correct_farmer && correct_wizard;
    }
};

const failed_check_message = {
    type: jsPsychHtmlButtonResponse,
    stimulus: "<p>You missed a question. Please read the instructions again.</p>",
    choices: ['Back to Instructions']
};

const if_node = {
    timeline: [failed_check_message],
    conditional_function: function () {
        const last_trial_correct = jsPsych.data.get().last(1).values()[0].correct;
        return !last_trial_correct;
    }
};

const instructions_and_comprehension_loop = {
    timeline: [
        instructions,
        attention_check,
        if_node
    ],
    loop_function: function () {
        const last_check_correct = jsPsych.data.get().filter({ trial_type: 'survey-html-form' }).last(1).values()[0].correct;
        return !last_check_correct;
    },
    on_timeline_finish: function () {
        jsPsych.setProgressBar(0.20);
    }
};
timeline.push(instructions_and_comprehension_loop);


// Transition
timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: '<p>Nice job! The main trials will now begin.</p>',
    choices: ['Start Trials'],
    on_finish: function () {
        jsPsych.setProgressBar(0.25);
    }
});

// Main Trials
const shuffled_trials = jsPsych.randomization.shuffle(ALL_PREFERENCE_TRIALS);

for (let i = 0; i < shuffled_trials.length; i++) {
    const trialParams = shuffled_trials[i];
    timeline.push({
        type: PreferenceGridworldTrialPlugin,
        trial_params: trialParams,
        on_finish: function (data) {
            const trials_completed = i + 1;
            const total_trials = shuffled_trials.length;
            const trial_progress = 0.25 + (trials_completed / total_trials) * 0.7;
            jsPsych.setProgressBar(trial_progress);
        }
    });
}

// Demographics
timeline.push({
    ...demographic,
    on_finish: function (data) {
        if (demographic.on_finish) demographic.on_finish(data);
        jsPsych.setProgressBar(0.95);
    }
});

// Save data
if (window.DataPipeSave) {
    timeline.push(window.DataPipeSave.save_trials);
    timeline.push(window.DataPipeSave.save_demographics);
} else {
    console.warn("DataPipeSave not found. Data saving will not work.");
}

// End
timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: `
        <h2>Thank You!</h2>
        <p>You have completed the experiment.</p>
        <p>You will be automatically redirected back to Prolific.</p>
        <p>Code: <strong>CNYPV5QR</strong></p>
    `,
    choices: [],
    trial_duration: 5000,
    on_start: function () {
        jsPsych.setProgressBar(1.0);
    }
});

jsPsych.run(timeline);
