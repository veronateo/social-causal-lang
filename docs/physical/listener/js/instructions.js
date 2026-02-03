/**
 * Listener Experiment Instructions
 */

const listenerInstructions = {
    type: jsPsychInstructions,
    pages: [
        // Page 1: Listener task introduction
        `<div class="instructions-container" style="max-width: 800px;">
            <p>In this next part, rather than selecting a sentence, you will see what description someone else chose. Your job is to figure out which scenario animation they saw. 
        </div>`,

        // Page 2: Setup explanation
        `<div class="instructions-container" style="max-width: 800px;">
            <p>On each trial, you will see which sentence the describer chose at the top, along with two candidate scenarios underneath.</p>
            <p> After you've played each animation at least once, a slider will appear under the animations. Use the slider to indicate which scenario you think the describer saw.
            </p>
        </div>`,

        // Page 3: Attention check notice
        `<div class="instructions-container" style="max-width: 800px;">
            <p>On the next page, there are several questions about the instructions. Please answer them carefully. You will not be able to proceed until you have answered them all correctly.</p> 
        </div>`
    ],
    show_clickable_nav: true,
    allow_backward: true,
    allow_keys: true,
    key_forward: 'ArrowRight',
    key_backward: 'ArrowLeft',
    button_label_previous: 'Previous',
    button_label_next: 'Next'
};
