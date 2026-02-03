/**
 * preference/speaker/js/instructions.js
 * 
 * Instructions and comprehension checks for the Preference Speaker Experiment.
 */

const instructions = {
    type: jsPsychInstructions,
    pages: [
        // Page 1: Welcome
        `<div class="instructions-container" style="max-width: 800px;">
            <h3>Welcome!</h3>
            <p>In this study, you will watch short animations of a farmer who wants to get some fruits. After each animation, you will be asked a question about what happened.</p>
        </div>`,

        // Page 2: Setup explanation
        `<div class="instructions-container" style="max-width: 700px;">
            <p>Each animation shows a path that contains two fruit baskets. The left basket always initially contains either one or two bananas, and the right basket has either one or two apples.</p>
            <img src="../../images/initial-baskets.png" class="instructions-image" alt="Initial setup of the trial" style="width: 100%;">
        </div>`,

        // Page 3: Wizard explanation
        `<div class="instructions-container" style="max-width: 700px;">
            <p>Below each path is a wizard with special powers.</p>
            <img src="../../images/initial-preference-wizard.png" class="instructions-image" alt="Wizard" style="width: 100%;">
        </div>`,

        // Page 4: Wizard can add to left (banana) basket
        `<div class="instructions-container">
            <div style="max-width: 700px; margin: 0 auto;">
                <p>For example, the wizard can add one apple to the left basket.</p>
                <p>The bolded tiles indicate the points at which the wizard can act. The wizard can only act once per trial, after observing the farmer's actions.</p>
            </div>
            <div id="demo-add-left" style="margin-top: 10px; margin-bottom: 0;">
                <canvas id="demoAddLeftCanvas" class="gw-canvas" style="margin: 10px auto 0 auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 5: Wizard can add to right (apple) basket
        `<div class="instructions-container">
            <div style="max-width: 700px; margin: 0 auto;">
                <p>The wizard can also add an apple to the right basket.</p>
            </div>
            <div id="demo-add-right" style="margin-top: 10px; margin-bottom: 0;">
                <canvas id="demoAddRightCanvas" class="gw-canvas" style="margin: 10px auto 0 auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 6: Wizard nothing demo
        `<div class="instructions-container">
            <div style="max-width: 700px; margin: 0 auto;">
                <p>Finally, the wizard can also choose to do nothing at all.</p>
            </div>
            <div id="demo-nothing" style="margin-top: 10px; margin-bottom: 0;">
                <canvas id="demoNothingCanvas" class="gw-canvas" style="margin: 10px auto 0 auto; display: block;"></canvas>
            </div>
        </div>`,

        // Page 7: Attention check notice
        `<div class="instructions-container" style="max-width: 700px;">
            <p>On the next page, we will ask you several questions about the instructions. Please answer them carefully. You will not be able to proceed until you have answered them all correctly.</p> 
        </div>`
    ],
    show_clickable_nav: true,
    on_load: function () {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const demoAddLeftCanvas = node.querySelector ? node.querySelector('#demoAddLeftCanvas') : (node.id === 'demoAddLeftCanvas' ? node : null);
                        const demoAddRightCanvas = node.querySelector ? node.querySelector('#demoAddRightCanvas') : (node.id === 'demoAddRightCanvas' ? node : null);
                        const demoNothingCanvas = node.querySelector ? node.querySelector('#demoNothingCanvas') : (node.id === 'demoNothingCanvas' ? node : null);

                        if (demoAddLeftCanvas && !demoAddLeftCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(demoAddLeftCanvas, window.InstructionTrials.instructionTrials[0], { startDelay: 15000, loopDelay: 2500 });
                                demoAddLeftCanvas.dataset.initialized = 'true';
                            }
                        }

                        if (demoAddRightCanvas && !demoAddRightCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(demoAddRightCanvas, window.InstructionTrials.instructionTrials[1], { startDelay: 5000, loopDelay: 2500 });
                                demoAddRightCanvas.dataset.initialized = 'true';
                            }
                        }

                        if (demoNothingCanvas && !demoNothingCanvas.dataset.initialized) {
                            if (window.InstructionTrials) {
                                setupDemoCanvas(demoNothingCanvas, window.InstructionTrials.instructionTrials[2], { startDelay: 5000, loopDelay: 2500 });
                                demoNothingCanvas.dataset.initialized = 'true';
                            }
                        }
                    }
                });
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }
};

function setupDemoCanvas(canvas, trialData, options = {}) {
    if (!canvas || !trialData) return;

    const renderer = new PreferenceGridWorldRenderer(canvas, {
        imageBasePath: '../../images',
        horizontalBorder: 80,
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
        img.onerror = resolve;
        img.src = `../../images/${type}.png`;
    }));

    Promise.all(imagePromises).then(() => {
        renderer.renderFrame(trialData, 0);

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

        setTimeout(() => {
            let firstCycleComplete = false;
            renderer.playAnimation(trialData, {
                loop: true,
                speed: 800,
                loopDelay: options.loopDelay || 2000,
                onFrameChange: (frameIndex) => {
                    // Enable Next button after first complete cycle
                    if (!firstCycleComplete && frameIndex === trialData.frames.length - 1) {
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
        }, options.startDelay || 5000);
    });
}
