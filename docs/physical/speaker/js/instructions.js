/**
 * js/instructions.js
 *
 * This file contains the instruction pages for the experiment.
 */

const instructions = {
    type: jsPsychInstructions,
    pages: [
        // Page 1: Welcome
        `<div class="instructions-container" style="max-width: 800px;">
            <h3>Welcome!</h3>
            <p>In this study, you will watch short animations of a farmer trying to get some fruit.</p> 
            <p>Sometimes, the farmer wants to get a banana, and other times, he wants an apple.</p> 
            <p>After each animation, you will be asked a question about what happened.</p>
        </div>`,

        // Page 2: Setup explanation
        `<div class="instructions-container">
            <p>Each animation shows a long path that contains a banana (left), an apple (right), and a farmer (middle).</p>
            <p>Below each path is a wizard with special powers.</p>
            <img src="../../images/initial.png" class="instructions-image" alt="Initial setup of the trial" style="width: 80%;">
        </div>`,

        // Page 3: Rock placement demo
        `<div class="instructions-container">
            <p>The wizard can choose to make a rock appear in the bolded grid cell.</p>
            <div id="place-rock-demo" style="margin: 20px 0;">
                <canvas id="placeRockCanvas" class="gw-canvas" style="margin: 10px auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 4: Rock removal demo
        `<div class="instructions-container">
            <p>The wizard can also choose to remove a rock from the bolded grid cell.</p>
            <div id="remove-rock-demo" style="margin: 20px 0;">
                <canvas id="removeRockCanvas" class="gw-canvas" style="margin: 10px auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 5: Wizard constraints
        `<div class="instructions-container" style="max-width: 800px;">
            <p>The wizard can act only once per trial.</p>
            <p>However, the wizard cannot act immediately at the beginning of each trial. The wizard must first observe the farmer's actions before it can raise its wand and decide what to do.</p>
        </div>`,

        // Page 6: Do nothing option
        `<div class="instructions-container">
            <p>Finally, the wizard can also choose to do nothing at all, even after raising its wand.</p>
        </div>`,

        // Page 7: Attention check notice
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
    button_label_next: 'Next',
    on_load: function () {
        // Set up a MutationObserver to watch for when canvas elements appear
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check if this node or its children contain our canvas elements
                        const placeRockCanvas = node.querySelector ? node.querySelector('#placeRockCanvas') :
                            (node.id === 'placeRockCanvas' ? node : null);
                        const removeRockCanvas = node.querySelector ? node.querySelector('#removeRockCanvas') :
                            (node.id === 'removeRockCanvas' ? node : null);

                        if (placeRockCanvas && !placeRockCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(placeRockCanvas, window.InstructionTrials.instructionTrials[0]);
                                placeRockCanvas.dataset.initialized = 'true';
                            }
                        }

                        if (removeRockCanvas && !removeRockCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(removeRockCanvas, window.InstructionTrials.instructionTrials[1]);
                                removeRockCanvas.dataset.initialized = 'true';
                            }
                        }
                    }
                });
            });
        });

        // Start observing the entire document for changes
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
};

// Helper function to set up demo canvases
function setupDemoCanvas(canvas, trialData) {
    if (!canvas || !trialData) {
        return;
    }

    const renderer = new GridWorldRenderer(canvas, {
        laneLength: 19,
        maxWidth: 1000,
        laneHeight: 90,
        animationSpeed: 1000,
        imageBasePath: '../../images'
    });

    // Load images first
    const imageTypes = ['farmer', 'wizard', 'wizard-wand', 'lightning', 'apple', 'banana', 'rock', 'thought'];
    const imagePromises = imageTypes.map(type => new Promise(resolve => {
        const img = new Image();
        img.onload = () => {
            renderer.images.set(type, img);
            resolve();
        };
        img.onerror = resolve;
        img.src = `../../images/${type}.png`;
    }));

    Promise.all(imagePromises).then(() => {
        // Show initial frame
        if (trialData.frames && trialData.frames.length > 0) {
            renderer.renderFrame(trialData, 0);
        }

        // Disable Next button initially
        const nextBtn = document.querySelector('#jspsych-instructions-next');
        if (nextBtn) {
            nextBtn.disabled = true;
            nextBtn.style.opacity = '0.5';
        }

        // Block keyboard navigation until demo completes
        let demoCompleted = false;
        const blockKeyboardHandler = (e) => {
            if (!demoCompleted && (e.key === 'ArrowRight' || e.code === 'ArrowRight')) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
            }
        };

        // Add keyboard blocker with high priority
        document.addEventListener('keydown', blockKeyboardHandler, true);

        // Start auto-playing looped animation after a short delay
        setTimeout(() => {
            let firstCycleComplete = false;

            renderer.playAnimation(trialData, {
                loop: true,
                onFrameChange: (frameIndex, frame) => {
                    // Enable Next button after first complete cycle
                    if (!firstCycleComplete && frameIndex === trialData.frames.length - 1) {
                        firstCycleComplete = true;
                        setTimeout(() => {
                            // Enable button
                            const nextBtn = document.querySelector('#jspsych-instructions-next');
                            if (nextBtn) {
                                nextBtn.disabled = false;
                                nextBtn.style.opacity = '1';
                            }

                            // Enable keyboard navigation
                            demoCompleted = true;
                            document.removeEventListener('keydown', blockKeyboardHandler, true);
                        }, 500);
                    }
                }
            });
        }, 1000);
    });
}
