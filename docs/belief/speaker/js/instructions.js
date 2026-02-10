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
            <p>In this study, you will watch short animations of a farmer trying to get a treasure chest with gold. After each animation, you will be asked a question about what happened.</p>
        </div>`,

        // Page 2: Setup explanation
        `<div class="instructions-container" style="max-width: 700px;">
            <p>Each animation shows a path that contains two treasure chests. One chest contains gold, and the other chest contains rocks. The farmer always wants to get the gold, but does not know which chest contains gold until he opens it.</p>
            <img src="../../images/initial-belief.png" class="instructions-image" alt="Initial setup of the trial" style="width: 100%;">
        </div>`,

        // Page 3: Farmer thought bubble explanation
        `<div class="instructions-container" style="max-width: 700px;">
            <p>In the beginning, the farmer might have no idea where the gold is located (indicated by the question mark next to the gold chest in the thought bubble). In some cases, the farmer has a guess about where the gold is (indicated by a right or left arrow next to the chest).</p>
            <p>In this example, the farmer does not have an initial guess about where the gold is.</p>
            <img src="../../images/initial-belief-thought.png" class="instructions-image" alt="Initial setup of the trial" style="width: 100%;">
        </div>`,

        // Page 4: Wizard explanation
        `<div class="instructions-container" style="max-width: 700px;">
            <p>Below each path is a wizard with special powers.</p>
            <img src="../../images/initial-belief-wizard.png" class="instructions-image" alt="Initial setup of the trial" style="width: 100%;">
        </div>`,

        // Page 5: Signpost demo
        `<div class="instructions-container">
            <div style="max-width: 700px; margin: 0 auto;">
                <p>The wizard can show where the gold treasure chest is by showing a sign.</p>
            </div>
            <div id="signpost-demo" style="margin-top: -10px; margin-bottom: 0;">
                <canvas id="signpostCanvas" class="gw-canvas" style="margin: 10px auto 0 auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 6: Farmer listen demo
        `<div class="instructions-container">
            <div style="max-width: 700px; margin: 0 auto;">
                <p>The farmer can choose to <i>listen</i> to the wizard, updating his belief about where the gold is located and moving in that direction.</p>
            </div>
            <div id="farmer-listen-demo" style="margin-top: 10px; margin-bottom: 0;">
                <canvas id="farmerListenCanvas" class="gw-canvas" style="margin: 10px auto 0 auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 7: Farmer ignore demo
        `<div class="instructions-container">
            <div style="max-width: 820px; margin: 0 auto;">
                <p>The farmer can also choose to <i>ignore</i> the wizard.</p>
                <p>In this example, the farmer has an initial guess that the gold is on the right. The wizard decides to show a sign pointing to the left. The farmer ignores the wizard and continues going right.</p>
            </div>
            <div id="farmer-ignore-demo" style="margin-top: -10px; margin-bottom: 0;">
                <canvas id="farmerIgnoreCanvas" class="gw-canvas" style="margin: 10px auto 0 auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 8: Wizard constraints
        `<div class="instructions-container" style="max-width: 800px;">
            <p>The wizard can act only once at the beginning of each trial, after observing the farmer.</p>
        </div>`,

        // Page 9: Wizard nothing demo
        `<div class="instructions-container">
            <p>Finally, the wizard can also choose to do nothing at all.</p>
            <div id="wizard-nothing-demo" style="margin-top: 10px; margin-bottom: 0;">
                <canvas id="wizardNothingCanvas" class="gw-canvas" style="margin: 10px auto 0 auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 10: Attention check notice
        `<div class="instructions-container" style="max-width: 700px;">
            <p>On the next page, we will ask you several questions about the instructions. Please answer them carefully. You will not be able to proceed until you have answered them all correctly.</p> 
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
                        const signpostCanvas = node.querySelector ? node.querySelector('#signpostCanvas') :
                            (node.id === 'signpostCanvas' ? node : null);
                        const farmerListenCanvas = node.querySelector ? node.querySelector('#farmerListenCanvas') :
                            (node.id === 'farmerListenCanvas' ? node : null);
                        const farmerIgnoreCanvas = node.querySelector ? node.querySelector('#farmerIgnoreCanvas') :
                            (node.id === 'farmerIgnoreCanvas' ? node : null);

                        if (signpostCanvas && !signpostCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(signpostCanvas, window.InstructionTrials.instructionTrials[0], { demoType: 'signpost' }, { startDelay: 8000 });
                                signpostCanvas.dataset.initialized = 'true';
                            }
                        }

                        if (farmerListenCanvas && !farmerListenCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(farmerListenCanvas, window.InstructionTrials.instructionTrials[1], { demoType: 'listen' }, { startDelay: 10000 });
                                farmerListenCanvas.dataset.initialized = 'true';
                            }
                        }

                        if (farmerIgnoreCanvas && !farmerIgnoreCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(farmerIgnoreCanvas, window.InstructionTrials.instructionTrials[2], { demoType: 'ignore' }, { startDelay: 11000 });
                                farmerIgnoreCanvas.dataset.initialized = 'true';
                            }
                        }

                        const wizardNothingCanvas = node.querySelector ? node.querySelector('#wizardNothingCanvas') :
                            (node.id === 'wizardNothingCanvas' ? node : null);

                        if (wizardNothingCanvas && !wizardNothingCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(wizardNothingCanvas, window.InstructionTrials.instructionTrials[3], { demoType: 'nothing' }, { startDelay: 5000 });
                                wizardNothingCanvas.dataset.initialized = 'true';
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
function setupDemoCanvas(canvas, trialData, options = {}, timing = {}) {
    if (!canvas || !trialData) {
        return;
    }

    const renderer = new BeliefGridWorldRenderer(canvas, {
        laneLength: 11,
        maxWidth: 900,
        laneHeight: 100,
        animationSpeed: 1000,
        imageBasePath: '../../images'
    });

    // Load images first
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
        img.onerror = resolve;
        img.src = `../../images/${type}.png`;
    }));

    Promise.all(imagePromises).then(() => {
        // Determine start and end frames based on demo type
        let startFrame = 0;
        let endFrame = trialData.frames.length - 1;

        if (options.demoType === 'signpost') {
            // Find the wizard's decision frame ("The wizard decides...")
            const decisionIndex = trialData.frames.findIndex(f => f.description && f.description.startsWith("The wizard decides"));

            // Start a few frames before to show "wizard looks" (considering)
            if (decisionIndex !== -1) {
                startFrame = Math.max(0, decisionIndex - 2);
                // End after the Reveal frame (decision + 1)
                endFrame = Math.min(trialData.frames.length - 1, decisionIndex + 1);
            }
        } else if (options.demoType === 'listen') {
            // Start after the signpost is revealed
            const decisionIndex = trialData.frames.findIndex(f => f.description && f.description.startsWith("The wizard decides"));
            if (decisionIndex !== -1) {
                startFrame = decisionIndex + 1;
            }
        }

        // Slice the frames to create the demo sequence
        const demoFrames = trialData.frames.slice(startFrame, endFrame + 1);

        // Find decision position from full trial data to ensure highlight works even if decision frame is sliced out
        let highlightTile;
        const decisionFrame = trialData.frames.find(f =>
            f.entities && f.entities.some(e => e.type === 'wizard' && e.withWand)
        );
        if (decisionFrame) {
            const farmer = decisionFrame.entities.find(e => e.type === 'farmer');
            if (farmer) highlightTile = farmer.position;
        }

        const demoTrialData = { ...trialData, frames: demoFrames, highlightTile: highlightTile };

        // Show initial frame of the demo
        if (demoFrames.length > 0) {
            renderer.renderFrame(demoTrialData, 0);
        }

        // Check if this demo has already been viewed
        window.completedDemos = window.completedDemos || new Set();
        const demoId = canvas.id;
        const isCompleted = window.completedDemos.has(demoId);

        // Disable Next button initially only if not already completed
        if (!isCompleted) {
            const nextBtn = document.querySelector('#jspsych-instructions-next');
            if (nextBtn) {
                nextBtn.disabled = true;
                nextBtn.style.opacity = '0.5';
            }
        }

        // Block keyboard navigation until demo completes (only if new)
        let demoCompleted = isCompleted; // If completed, start as true
        const blockKeyboardHandler = (e) => {
            if (!demoCompleted && (e.key === 'ArrowRight' || e.code === 'ArrowRight')) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
            }
        };

        // Add keyboard blocker with high priority
        if (!isCompleted) {
            document.addEventListener('keydown', blockKeyboardHandler, true);
        }

        // Start auto-playing looped animation after a short delay
        setTimeout(() => {
            let firstCycleComplete = false;

            renderer.playAnimation(demoTrialData, {
                loop: true,
                loopDelay: 2000,
                onFrameChange: (frameIndex, frame) => {
                    // Enable Next button after first complete cycle
                    if (!firstCycleComplete && frameIndex === demoFrames.length - 1) {
                        firstCycleComplete = true;
                        window.completedDemos.add(demoId); // Mark as verified seen

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
        }, timing.startDelay || 5000);
    });
}

