/**
 * belief/speaker/js/experiment.js
 *
 * This file contains the core logic for the Belief Domain Speaker Experiment.
 */

const jsPsych = initJsPsych({
    show_progress_bar: true,
    message_progress_bar: 'Completion Progress',
    on_finish: function () {
        // Redirect to Prolific completion URL
        const prolific_completion_url = "https://app.prolific.com/submissions/complete?cc=CV24Z7Q9";
        window.location.href = prolific_completion_url;
    },
    override_safe_mode: true
});

/**
 * Custom jsPsych plugin for the belief grid world trial.
 */
class BeliefGridworldTrialPlugin {
    constructor(jsPsych) {
        this.jsPsych = jsPsych;
    }

    static info = {
        name: 'belief-gridworld-trial',
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
        // Log trial ID for debugging
        if (trial.trial_params && trial.trial_params.id) {
            console.log('Trial ID:', trial.trial_params.id);
        }

        const isDemo = trial.demo_mode || false;

        // Generate the actual trial frames using the generator
        const generator = new BeliefTrialGenerator();
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
                            <label for="opt1">The wizard <strong>caused</strong> the farmer to get ${trialData.outcome}.</label>
                        </div>
                        <div class="gw-option" style="margin-bottom: 10px;">
                            <input type="radio" name="causalQuestion" id="opt2" value="enabled" required>
                            <label for="opt2">The wizard <strong>enabled</strong> the farmer to get ${trialData.outcome}.</label>
                        </div>
                        <div class="gw-option" style="margin-bottom: 10px;">
                            <input type="radio" name="causalQuestion" id="opt3" value="allowed" required>
                            <label for="opt3">The wizard <strong>allowed</strong> the farmer to get ${trialData.outcome}.</label>
                        </div>
                        <div class="gw-option" style="margin-bottom: 10px;">
                            <input type="radio" name="causalQuestion" id="opt4" value="made_no_difference" required>
                            <label for="opt4">The wizard <strong>made no difference</strong> to the farmer getting ${trialData.outcome}.</label>
                        </div>
                        <button type="submit" id="submitBtn" class="jspsych-btn btn-blue" style="margin-top: 20px; margin-bottom: 40px; display: block; margin-left: auto; margin-right: auto;" disabled>Submit</button>
                    </form>
                </div>`;
        }

        html += `
            </div>
        `;
        display_element.innerHTML = html;
        const startTime = performance.now();

        const canvas = document.getElementById('gridCanvas');
        // Initialize renderer with belief-specific config
        const renderer = new BeliefGridWorldRenderer(canvas, {
            imageBasePath: '../../images',
            horizontalBorder: 80
        });

        const imageTypes = [
            'farmer', 'wizard', 'wizard-wand', 'lightning',
            'treasure-closed', 'treasure-gold', 'treasure-rocks',
            'thought', 'thought-middle', 'signpost-left', 'signpost-right'
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
            // Auto-play animation for demos
            setTimeout(() => {
                let firstAnimationComplete = false;
                renderer.playAnimation(trialData, {
                    loop: true,
                    speed: 700,
                    onFrameChange: (frameIndex) => {
                        // Enable continue button after first complete cycle
                        if (!firstAnimationComplete && frameIndex === trialData.frames.length - 1) {
                            firstAnimationComplete = true;
                            setTimeout(() => {
                                const continueBtn = document.getElementById('continueBtn');
                                if (continueBtn) {
                                    continueBtn.disabled = false;
                                }
                            }, 500);
                        }
                    }
                });
            }, 1000);

            // Demo mode continue
            const continueBtn = document.getElementById('continueBtn');
            if (continueBtn) {
                continueBtn.addEventListener('click', () => {
                    renderer.stopAnimation();
                    display_element.innerHTML = '';
                    this.jsPsych.finishTrial({ demo: true });
                });
            }
        } else {
            // Regular trial mode
            const playBtn = document.getElementById('playBtn');
            const replayBtn = document.getElementById('replayBtn');
            const submitBtn = document.getElementById('submitBtn');
            const radioButtons = display_element.querySelectorAll('input[name="causalQuestion"]');
            const prompt = document.querySelector('.gw-prompt');

            const playAnimation = (isReplay = false) => {
                replayBtn.disabled = true;
                if (!isReplay) {
                    playBtn.disabled = true;
                }
                renderer.playAnimation(trialData, {
                    loop: false,
                    speed: 800,
                    onComplete: () => {
                        setTimeout(() => {
                            if (!isReplay) {
                                playBtn.style.display = 'none';
                                replayBtn.style.display = 'inline-block';
                                document.getElementById('gw-question-container').style.visibility = 'visible';
                            }
                            replayBtn.disabled = false;
                            prompt.innerText = 'Please answer the question below.';
                        }, 500);
                    }
                });
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
                    response: document.querySelector('input[name="causalQuestion"]:checked').value,
                    rt: Math.round(performance.now() - startTime),
                    // Save relevant trial params
                    intervention: trial.trial_params.beliefIntervention,
                    outcome: trialData.outcome,
                    gold_pos: trial.trial_params.treasurePositions.gold
                };

                display_element.innerHTML = '';
                this.jsPsych.finishTrial(trial_data_to_save);
            });
        }
    }
}

let timeline = [];

// Preload images
timeline.push({
    type: jsPsychPreload,
    images: [
        '../../images/farmer.png', '../../images/wizard.png', '../../images/wizard-wand.png',
        '../../images/lightning.png', '../../images/treasure-closed.png',
        '../../images/treasure-gold.png', '../../images/treasure-rocks.png',
        '../../images/thought.png', '../../images/thought-middle.png',
        '../../images/signpost-left.png', '../../images/signpost-right.png',
        '../../images/initial-belief.png', '../../images/initial-belief-thought.png', '../../images/initial-belief-wizard.png'
    ]
});

// Consent
timeline.push({
    ...consent,
    on_finish: function (data) {
        if (consent.on_finish) {
            consent.on_finish(data);
        }
        jsPsych.setProgressBar(0.10);
    }
});

// Attention Check
const attention_check = {
    type: jsPsychSurveyHtmlForm,
    preamble: '<h3>Comprehension Check</h3><p>Please answer the following questions to continue.</p>',
    html: `
        <div class="jspsych-content" style="max-width: 700px; text-align: left;">
            <p style="font-weight: bold; margin-bottom: 1em;">1. What is the farmer's goal? <span style="color: red;">*</span></p>
            <div style="padding-left: 2em;"> 
                <p><input type="radio" name="farmer_goal" value="To get the gold treasure chest" required> To get the gold treasure chest</p>
                <p><input type="radio" name="farmer_goal" value="To talk to the wizard" required> To talk to the wizard</p>
                <p><input type="radio" name="farmer_goal" value="To plant seeds" required> To plant seeds</p>
            </div>
            <p style="margin-top: 2em; font-weight: bold; margin-bottom: 1em;">2. What can the wizard do? (select all that apply) <span style="color: red;">*</span></p>
            <div style="padding-left: 2em;">
                <p><input type="checkbox" name="wizard_nothing" value="Do nothing"> Do nothing</p>
                <p><input type="checkbox" name="wizard_move" value="Move the treasure"> Move the treasure</p>
                <p><input type="checkbox" name="wizard_sign" value="Show a signpost"> Show a signpost</p>
                <p><input type="checkbox" name="wizard_rain" value="Make it rain"> Make it rain</p>
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
                const radioButton = document.querySelector('input[name="farmer_goal"]:checked');
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
        const correct_farmer = data.response.farmer_goal === 'To get the gold treasure chest';
        const correct_wizard =
            data.response.wizard_sign &&
            data.response.wizard_nothing &&
            !data.response.wizard_move &&
            !data.response.wizard_rain;

        data.correct = correct_farmer && correct_wizard;
    }
};

const failed_check_message = {
    type: jsPsychHtmlButtonResponse,
    stimulus: "<p>You missed a question. Please carefully read the instructions again.</p>",
    choices: ['Back to Instructions']
};

const if_node = {
    timeline: [failed_check_message],
    conditional_function: function () {
        const last_trial_correct = jsPsych.data.get().last(1).values()[0].correct;
        return !last_trial_correct;
    }
};

// Instructions and comprehension loop
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

timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: '<p>Nice job! The main trials will now begin.</p>',
    choices: ['Start Trials'],
    on_finish: function () {
        jsPsych.setProgressBar(0.25);
    }
});

// Main Trials
// ALL_BELIEF_TRIALS is defined in trial-data.js
const shuffled_trials = jsPsych.randomization.shuffle(ALL_BELIEF_TRIALS);

for (let i = 0; i < shuffled_trials.length; i++) {
    const trialParams = shuffled_trials[i];
    timeline.push({
        type: BeliefGridworldTrialPlugin,
        trial_params: trialParams,
        on_finish: function (data) {
            const trials_completed = i + 1;
            const total_trials = shuffled_trials.length;

            const trial_progress = 0.25 + (trials_completed / total_trials) * 0.7;
            jsPsych.setProgressBar(trial_progress);
        }
    });
}

// Feedback / Demographics
timeline.push({
    ...demographic,
    on_finish: function (data) {
        if (demographic.on_finish) {
            demographic.on_finish(data);
        }
        jsPsych.setProgressBar(0.95);
    }
});

// Save Data
timeline.push(window.DataPipeSave.save_trials);
timeline.push(window.DataPipeSave.save_demographics);

// End
timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: `
        <h2>Thank You!</h2>
        <p>You have completed the experiment.</p>
        <p>You will be automatically redirected back to Prolific in a few moments.</p>
        <p>If you are not redirected, you can use the following code: <strong>CV24Z7Q9</strong></p>
    `,
    choices: [],
    trial_duration: 5000,
    on_start: function () {
        jsPsych.setProgressBar(1.0);
    }
});

// Run
jsPsych.run(timeline);
