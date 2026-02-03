/**
 * Belief Trial Generator
 * Creates trial data for belief intervention experiments.
 * Generates sequences for belief manipulation trials.
 */
class BeliefTrialGenerator {
    constructor(config = {}) {
        this.config = {
            farmerStartPos: 5,
            wizardPos: 5,
            goldPos: 10,
            rocksPos: 0,
            wizardTriggerPos: 7,
            ...config
        };
    }

    /**
     * Generates a complete belief trial
     * @param {Object} params - Trial parameters
     * @param {string} params.id - Trial ID
     * @param {string} params.label - Short trial label
     * @param {string} params.description - Trial description
     * @param {string} params.beliefIntervention - Type of belief intervention (e.g., 'no_belief_to_true')
     * @param {Object} params.initialBelief - { state: 'no_belief' | 'treasure_belief', goldDir: 'left'|'right' }
     * @param {Object} params.finalBelief - { state: 'treasure_belief', goldDir: 'left'|'right' }
     * @param {string} params.wizardAction - 'show_signpost' | 'nothing'
     * @param {Object} params.signpostContent - { truthful: boolean, goldLeft: boolean }
     * @param {string} params.finalOutcome - 'gold' | 'rocks'
     * @param {Object} params.treasurePositions - { gold: 'left'|'right', rocks: 'left'|'right' }
     */
    /**
     * Helper: Create wizard thought bubbles
     * @param {string} state - 'considering' | 'acting'
     * @param {string} action - 'show_signpost' | 'nothing'
     * @param {Object} signpostContent - { goldLeft: boolean }
     */
    _createWizardThoughtBubbles(state, action = null, signpostContent = null) {
        if (state === 'considering') {
            return {
                left: { action: 'point_left' },
                middle: { action: 'do_nothing' },
                right: { action: 'point_right' }
            };
        } else if (state === 'acting') {
            if (action === 'show_signpost') {
                if (signpostContent && signpostContent.goldLeft) {
                    return { left: { action: 'point_left' } };
                } else {
                    return { right: { action: 'point_right' } };
                }
            } else {
                return { middle: { action: 'do_nothing' } };
            }
        }
        return null;
    }

    /**
     * Generates a complete belief trial
     * @param {Object} params - Trial parameters
     * @param {string} params.id - Trial ID
     * @param {string} params.label - Short trial label
     * @param {string} params.description - Trial description
     * @param {string} params.beliefIntervention - Type of belief intervention (e.g., 'no_belief_to_true')
     * @param {Object} params.initialBelief - { state: 'no_belief' | 'treasure_belief', goldDir: 'left'|'right' }
     * @param {Object} params.finalBelief - { state: 'treasure_belief', goldDir: 'left'|'right' }
     * @param {string} params.wizardAction - 'show_signpost' | 'nothing'
     * @param {Object} params.signpostContent - { truthful: boolean, goldLeft: boolean }
     * @param {string} params.finalOutcome - 'gold' | 'rocks'
     * @param {Object} params.treasurePositions - { gold: 'left'|'right', rocks: 'left'|'right' }
     */
    generateTrial(params) {
        const {
            id,
            label,
            description,
            beliefIntervention,
            initialBelief,
            finalBelief,
            wizardAction,
            signpostContent,
            farmerPreference,
            finalOutcome,
            treasurePositions,
            farmerIgnoresWizard,
            instructionOnly
        } = params;

        const goldPos = treasurePositions.gold === 'left' ? 0 : 10;
        const rocksPos = treasurePositions.rocks === 'left' ? 0 : 10;

        let frames = [];

        // Initial entities
        let currentEntities = [
            { type: 'farmer', position: this.config.farmerStartPos },
            { type: 'wizard', position: this.config.wizardPos },
            { type: 'chest-left', position: 0, opened: false },
            { type: 'chest-right', position: 10, opened: false },
        ];

        // STEP 1: Initial state with farmer's belief
        // Wizard is considering from the start
        let initialWizardBubbles = this._createWizardThoughtBubbles('considering');

        frames.push({
            entities: [...currentEntities],
            action: null,
            thoughtBubbles: {
                ...this._createFarmerThoughtBubble(initialBelief),
                wizard: initialWizardBubbles
            },
            description: "",
            duration: 3000
        });

        // STEP 2: Wizard knowledge (can see where gold is)
        frames.push({
            entities: [...currentEntities],
            action: null,
            thoughtBubbles: {
                ...this._createFarmerThoughtBubble(initialBelief),
                wizard: initialWizardBubbles
            },
            description: "",
            duration: 3000
        });

        // STEP 3: Wizard decision point (raises wand)
        currentEntities = currentEntities.map(e =>
            e.type === 'wizard' ? { ...e, withWand: true, highlighted: true } : e
        );

        // Add wizard thought bubbles (considering)
        let step4Bubbles = this._createFarmerThoughtBubble(initialBelief);
        if (!step4Bubbles) step4Bubbles = {};
        step4Bubbles.wizard = this._createWizardThoughtBubbles('considering');

        frames.push({
            entities: [...currentEntities],
            action: null,
            thoughtBubbles: step4Bubbles,
            description: 'The wizard considers intervening'
        });

        // STEP 4: Wizard action (show signpost or do nothing)
        let step5Bubbles = this._createFarmerThoughtBubble(initialBelief);
        if (!step5Bubbles) step5Bubbles = {};

        let selectionBubbles = {};
        if (wizardAction === 'show_signpost') {
            if (signpostContent.goldLeft) {
                selectionBubbles = { left: { action: 'point_left' } };
            } else {
                selectionBubbles = { right: { action: 'point_right' } };
            }
        } else {
            selectionBubbles = { middle: { action: 'do_nothing' } };
        }

        step5Bubbles.wizard = selectionBubbles;

        // Determine action description
        let actionDesc = "The wizard decides to do nothing.";
        if (wizardAction === 'show_signpost') {
            actionDesc = signpostContent.goldLeft
                ? "The wizard decides to show that the gold is to the left."
                : "The wizard decides to show that the gold is to the right.";
        }

        frames.push({
            entities: [...currentEntities],
            action: null,
            thoughtBubbles: {
                ...step5Bubbles,
                wizard: selectionBubbles
            },
            description: actionDesc,
            duration: 1500
        });

        // Wizard lowers wand
        currentEntities = currentEntities.map(e =>
            e.type === 'wizard' ? { ...e, withWand: false, highlighted: false } : e
        );

        let revealBubbles = this._createFarmerThoughtBubble(initialBelief);
        if (!revealBubbles) revealBubbles = {};

        // Only show persistent content if it's a signpost
        if (wizardAction === 'show_signpost') {
            if (signpostContent.goldLeft) {
                revealBubbles.wizard = { left: { action: 'point_left', noBubble: true } };
            } else {
                revealBubbles.wizard = { right: { action: 'point_right', noBubble: true } };
            }
        } else {
            // If doing nothing, bubble disappears entirely
            revealBubbles.wizard = null;
        }

        // Store this for future frames
        const finalWizardBubbles = revealBubbles.wizard;

        frames.push({
            entities: [...currentEntities],
            action: null,
            thoughtBubbles: revealBubbles,
            description: actionDesc,
            duration: 2000
        });

        // Update step5Bubbles to use the finalized state for subsequent frames to inherit
        step5Bubbles.wizard = finalWizardBubbles;

        // STEP 5: Updated farmer belief (if changed or ignored)
        const beliefChanged = this._beliefsAreDifferent(initialBelief, finalBelief);
        const farmerPos = currentEntities.find(e => e.type === 'farmer').position;

        // Track if signpost is present for remaining frames
        const hasSignpost = wizardAction === 'show_signpost';

        if (beliefChanged || farmerIgnoresWizard) {
            let thoughtBubbles;
            let description;
            var customFramesAdded = false;

            if (farmerIgnoresWizard) {
                // Calculate what wizard's signpost suggests
                let wizardSuggestedBelief;
                if (hasSignpost && signpostContent) {
                    wizardSuggestedBelief = {
                        state: 'treasure_belief',
                        goldDir: signpostContent.goldLeft ? 'left' : 'right'
                    };
                } else {
                    // Fallback if no signpost (shouldn't happen for ignore trials usually)
                    wizardSuggestedBelief = {
                        state: 'treasure_belief',
                        goldDir: initialBelief.goldDir === 'left' ? 'right' : 'left'
                    };
                }

                // Determine what the farmer chose
                let chosenBelief;
                if (initialBelief.state === 'no_belief') {
                    if (wizardAction === 'do_nothing') {
                        // case 1: No initial belief + Wizard does nothing
                        // Just keep the initial bubble (question mark)
                        thoughtBubbles = this._createFarmerThoughtBubble(initialBelief);
                        customFramesAdded = false;
                        thoughtBubbles = this._createFarmerThoughtBubble(initialBelief);
                    } else {
                        // case 2: No initial belief + Wizard shows sign + Ignore
                        // 3 Bubbles: Left (?), Middle (Wizard), Right (Farmer Choice)

                        chosenBelief = { ...finalBelief, chosen: true };
                        const direction = chosenBelief.goldDir === 'left' ? 'left' : 'right';
                        const ignoreDescription = `The farmer ignores the wizard and goes to the ${direction}.`;
                        const considerDescription = '';

                        // FRAME 1: Left (?) + Middle (Wizard Sign)
                        const frame1Bubbles = {
                            farmer: {
                                left: initialBelief, // ?
                                middle: wizardSuggestedBelief // Sign
                            },
                            wizard: step5Bubbles.wizard
                        };

                        frames.push({
                            entities: [...currentEntities],
                            action: { type: 'belief_change', farmerPosition: farmerPos, entities: currentEntities },
                            thoughtBubbles: frame1Bubbles,
                            description: considerDescription,
                            duration: 2000
                        });

                        // FRAME 2: Left (?) + Middle (Wizard Sign) - Still considering/ignoring
                        const frame2Bubbles = JSON.parse(JSON.stringify(frame1Bubbles));
                        // Keep opacity 1.0 for now
                        if (frame2Bubbles.farmer.middle) frame2Bubbles.farmer.middle.alpha = 1.0;

                        frames.push({
                            entities: [...currentEntities],
                            action: { type: 'belief_change', farmerPosition: farmerPos, entities: currentEntities },
                            thoughtBubbles: frame2Bubbles,
                            description: considerDescription,
                            duration: 1000
                        });

                        // FRAME 3: Left (?) + Middle (Sign) + Right (Chosen) - All visible
                        const frame3Bubbles = JSON.parse(JSON.stringify(frame2Bubbles));
                        frame3Bubbles.farmer.right = chosenBelief;
                        if (frame3Bubbles.farmer.right) frame3Bubbles.farmer.right.alpha = 1.0;
                        // Keep left/middle opaque for this frame so "right appears" first
                        if (frame3Bubbles.farmer.left) frame3Bubbles.farmer.left.alpha = 1.0;
                        if (frame3Bubbles.farmer.middle) frame3Bubbles.farmer.middle.alpha = 1.0;

                        frames.push({
                            entities: [...currentEntities],
                            action: { type: 'belief_change', farmerPosition: farmerPos, entities: currentEntities },
                            thoughtBubbles: frame3Bubbles,
                            description: considerDescription,
                            duration: 1000
                        });

                        // FRAME 4: Left/Middle Fade Out (Decision Finalized)
                        const frame4Bubbles = JSON.parse(JSON.stringify(frame3Bubbles));
                        if (frame4Bubbles.farmer.left) frame4Bubbles.farmer.left.alpha = 0.3;
                        if (frame4Bubbles.farmer.middle) frame4Bubbles.farmer.middle.alpha = 0.3;

                        frames.push({
                            entities: [...currentEntities],
                            action: { type: 'belief_change', farmerPosition: farmerPos, entities: currentEntities },
                            thoughtBubbles: frame4Bubbles,
                            description: ignoreDescription,
                            duration: 1000
                        });

                        thoughtBubbles = frame4Bubbles;
                        customFramesAdded = true;

                        thoughtBubbles = frame3Bubbles;
                        customFramesAdded = true;
                    }

                } else {
                    chosenBelief = { ...initialBelief, chosen: true };
                    const ignoreDirection = chosenBelief.goldDir === 'left' ? 'left' : 'right';
                    const ignoreDescription = `The farmer ignores the wizard and goes to the ${ignoreDirection}.`;

                    // Standard ignore bubble logic
                    const standardIgnoreBubbles = this._createFarmerThoughtBubble(chosenBelief, wizardSuggestedBelief);

                    // Determine descriptions
                    const isInstruction = instructionOnly;

                    let frame1Desc = '';
                    // Always use wizard text for Frame 1 so the "ignore" text appears only when the bubble fades (Frame 2)
                    const signDir = (signpostContent && signpostContent.goldLeft) ? 'left' : 'right';
                    frame1Desc = `The wizard decides to show that the gold is to the ${signDir}.`;

                    // FRAME 1: Decision/Comparison Phase - Both Opaque
                    const frame1Bubbles = JSON.parse(JSON.stringify(standardIgnoreBubbles));
                    if (frame1Bubbles.farmer.initial) frame1Bubbles.farmer.initial.alpha = 1.0;
                    if (frame1Bubbles.farmer.updated) frame1Bubbles.farmer.updated.alpha = 1.0;
                    frame1Bubbles.wizard = finalWizardBubbles;

                    frames.push({
                        entities: [...currentEntities],
                        action: {
                            type: 'belief_change',
                            farmerPosition: farmerPos,
                            entities: currentEntities,
                        },
                        thoughtBubbles: frame1Bubbles,
                        description: frame1Desc,
                        duration: 1500
                    });

                    // FRAME 2: Rejection Phase - Wizard Bubble Fades
                    const frame2Bubbles = JSON.parse(JSON.stringify(frame1Bubbles));
                    if (frame2Bubbles.farmer.updated) frame2Bubbles.farmer.updated.alpha = 0.3;
                    frame2Bubbles.wizard = finalWizardBubbles;

                    frames.push({
                        entities: [...currentEntities],
                        action: {
                            type: 'belief_change',
                            farmerPosition: farmerPos,
                            entities: currentEntities
                        },
                        thoughtBubbles: frame2Bubbles,
                        description: ignoreDescription,
                        duration: 1500
                    });

                    thoughtBubbles = frame2Bubbles;
                    customFramesAdded = true;
                }
            } else {
                if (initialBelief.state === 'no_belief' && wizardAction === 'nothing') {
                    // Suppress additional bubbles for "No Belief + Do Nothing" case
                    thoughtBubbles = this._createFarmerThoughtBubble(initialBelief);
                    description = 'Farmer makes a decision without help';
                } else {
                    // Normal belief change - Split into Comparison and Acceptance (Standard Listen Logic)

                    // 1. Wizard Description
                    let wizardDesc = "";
                    if (wizardAction === 'show_signpost') {
                        const signDir = (signpostContent && signpostContent.goldLeft) ? 'left' : 'right';
                        wizardDesc = `The wizard decides to show that the gold is to the ${signDir}.`;
                    } else {
                        wizardDesc = "The wizard decides to do nothing.";
                    }

                    // 2. Farmer Description
                    const beliefDir = finalBelief.goldDir === 'left' ? 'left' : 'right';
                    const farmerDesc = `The farmer believes the wizard and goes to the ${beliefDir}.`;

                    // Base bubbles
                    const baseBubbles = this._createFarmerThoughtBubble(initialBelief, finalBelief);

                    // FRAME 1: Comparison (Wizard Text, Opaque Bubbles)
                    const frame1Bubbles = JSON.parse(JSON.stringify(baseBubbles));
                    if (frame1Bubbles.farmer.initial) frame1Bubbles.farmer.initial.alpha = 1.0;
                    if (frame1Bubbles.farmer.updated) frame1Bubbles.farmer.updated.alpha = 1.0;
                    frame1Bubbles.wizard = finalWizardBubbles;

                    frames.push({
                        entities: [...currentEntities],
                        action: {
                            type: 'belief_change',
                            farmerPosition: farmerPos,
                            entities: currentEntities,
                        },
                        thoughtBubbles: frame1Bubbles,
                        description: wizardDesc,
                        duration: 1500
                    });

                    // FRAME 2: Acceptance (Farmer Text, Initial Fades)
                    const frame2Bubbles = JSON.parse(JSON.stringify(frame1Bubbles));
                    if (frame2Bubbles.farmer.initial) frame2Bubbles.farmer.initial.alpha = 0.3; // Initial fades
                    frame2Bubbles.wizard = finalWizardBubbles;

                    frames.push({
                        entities: [...currentEntities],
                        action: {
                            type: 'belief_change',
                            farmerPosition: farmerPos,
                            entities: currentEntities
                        },
                        thoughtBubbles: frame2Bubbles,
                        description: farmerDesc,
                        duration: 1500
                    });

                    thoughtBubbles = frame2Bubbles;
                    customFramesAdded = true;
                }
            }

            if (!thoughtBubbles) thoughtBubbles = {};
            thoughtBubbles.wizard = finalWizardBubbles;

            if (!customFramesAdded) {
                // Create a copy of bubbles with full opacity for this frame only
                const beliefChangeBubbles = JSON.parse(JSON.stringify(thoughtBubbles));
                if (beliefChangeBubbles.farmer && beliefChangeBubbles.farmer.initial && beliefChangeBubbles.farmer.updated) {
                    beliefChangeBubbles.farmer.initial.alpha = 1.0;
                    beliefChangeBubbles.farmer.updated.alpha = 1.0;
                }

                frames.push({
                    entities: [...currentEntities],
                    action: {
                        type: 'belief_change',
                        farmerPosition: farmerPos,
                        entities: currentEntities
                        // signpostData removed
                    },
                    thoughtBubbles: beliefChangeBubbles,
                    description,
                    duration: 2000
                });
            }
        }

        // STEP 6: Farmer moves to chest and opens it
        // Determine target position based on final belief
        const targetPos = this._getTargetFromBelief(finalBelief, farmerPreference, goldPos, rocksPos);

        // Calculate path to target
        let currentPos = farmerPos;
        const step = targetPos > currentPos ? 1 : -1;

        // After belief change, show both bubbles (with faded initial)
        // For ignore trials, keep showing chosen initial belief vs wizard's suggestion
        let thoughtBubblesForMovement;
        if (farmerIgnoresWizard) {
            const wizardSuggestedBelief = {
                state: 'treasure_belief',
                goldDir: signpostContent && signpostContent.goldLeft ? 'left' : 'right'
            };

            let chosenBelief;
            if (initialBelief.state === 'no_belief') {
                chosenBelief = { ...finalBelief, chosen: true };
                // Reconstruct 3-bubble state for movement (Left/Middle Faded, Right Full)
                thoughtBubblesForMovement = {
                    farmer: {
                        left: { ...initialBelief, alpha: 0.3 },
                        middle: { ...wizardSuggestedBelief, alpha: 0.3 },
                        right: { ...chosenBelief, alpha: 1.0 }
                    }
                };
            } else {
                chosenBelief = { ...initialBelief, chosen: true };
                thoughtBubblesForMovement = this._createFarmerThoughtBubble(chosenBelief, wizardSuggestedBelief);
            }
        } else if (initialBelief.state === 'no_belief' && wizardAction === 'nothing') {
            thoughtBubblesForMovement = this._createFarmerThoughtBubble(initialBelief);
        } else if (beliefChanged) {
            thoughtBubblesForMovement = this._createFarmerThoughtBubble(initialBelief, finalBelief);
        } else {
            thoughtBubblesForMovement = this._createFarmerThoughtBubble(finalBelief);
        }

        if (!thoughtBubblesForMovement) thoughtBubblesForMovement = {};
        thoughtBubblesForMovement.wizard = finalWizardBubbles;

        // Determine description for movement phase
        let movementDescription = 'Farmer decides action';
        if (farmerIgnoresWizard) {
            const chosenBelief = { ...finalBelief, chosen: true };
            const direction = chosenBelief.goldDir === 'left' ? 'left' : 'right';
            movementDescription = `The farmer ignores the wizard and goes to the ${direction}.`;
        }

        // Show decision frame (static at start position with updated bubbles)
        frames.push({
            entities: [...currentEntities],
            action: {
                type: 'belief_change', // Continue showing belief change state
                farmerPosition: farmerPos,
                entities: currentEntities
                // signpostData removed
            },
            thoughtBubbles: thoughtBubblesForMovement,
            description: movementDescription,
            duration: 2000
        });

        // Move toward target chest (stop at position 1 or 9, one cell before chest)
        const stopPosition = targetPos === 0 ? 1 : 9;

        let stepsTaken = 0;
        while (currentPos !== stopPosition) {
            currentPos += step;
            stepsTaken++;

            currentEntities = currentEntities.map(e =>
                e.type === 'farmer' ? { ...e, position: currentPos, highlighted: true } : e
            );

            frames.push({
                entities: [...currentEntities],
                action: {
                    type: 'move',
                    farmerPosition: currentPos,
                    entities: currentEntities
                },
                thoughtBubbles: thoughtBubblesForMovement,
                description: movementDescription,
                duration: 700
            });
        }

        // Farmer opens the chest
        const targetChestType = targetPos === 0 ? 'chest-left' : 'chest-right';
        const chestContents = targetPos === goldPos ? 'gold' : 'rocks';

        currentEntities = currentEntities.map(e =>
            e.type === targetChestType ? { ...e, opened: true, contents: chestContents } : e
        );

        let finalBubbles = thoughtBubblesForMovement;
        if (!finalBubbles) finalBubbles = {};
        finalBubbles.wizard = finalWizardBubbles;

        frames.push({
            entities: [...currentEntities],
            action: {
                type: 'show_signpost'
            },
            thoughtBubbles: finalBubbles,
            description: farmerIgnoresWizard ? movementDescription : `Farmer opens chest and finds ${chestContents}`,
            duration: 1000
        });

        return {
            id,
            label,
            description,
            beliefIntervention,
            outcome: `the ${finalOutcome}`,
            frames
        };
    }

    /**
     * Helper: Create farmer thought bubble based on belief state
     * Can show either single belief or initial + updated beliefs
     * @param {Object} belief - Current belief state
     * @param {Object} updatedBelief - Optional updated belief (for showing both)
     */
    _createFarmerThoughtBubble(belief, updatedBelief = null) {
        if (!belief) return null;

        const beliefData = this._formatBeliefForBubble(belief);

        // If we have both initial and updated beliefs, show both bubbles
        if (updatedBelief) {
            return {
                farmer: {
                    initial: beliefData,
                    updated: this._formatBeliefForBubble(updatedBelief)
                }
            };
        }

        // Otherwise, show single belief
        return { farmer: beliefData };
    }

    /**
     * Helper: Format belief for thought bubble display
     */
    _formatBeliefForBubble(belief) {
        if (belief.state === 'no_belief') {
            return { state: 'no_belief' };
        } else if (belief.state === 'treasure_belief') {
            const formatted = {
                state: 'treasure_belief',
                goldDir: belief.goldDir
            };
            // Preserve chosen flag if present
            if (belief.chosen) {
                formatted.chosen = true;
            }
            return formatted;
        }
        return null;
    }

    /**
     * Helper: Determine initial movement direction based on belief
     */
    _getInitialDirection(belief, preference, treasurePositions) {
        if (!belief || belief.state === 'no_belief') {
            // If no belief, farmer doesn't move initially
            return null;
        }

        // If farmer has belief, move toward where they think gold is
        return belief.goldDir;
    }

    /**
     * Helper: Determine final movement direction based on updated belief
     */
    _getFinalDirection(belief, preference, treasurePositions) {
        if (!belief || belief.state === 'no_belief') {
            // This shouldn't happen in final belief, but handle it
            return 'right';
        }

        return belief.goldDir;
    }

    /**
     * Helper: Check if two beliefs are different
     */
    _beliefsAreDifferent(belief1, belief2) {
        if (!belief1 || !belief2) return true;
        if (belief1.state !== belief2.state) return true;

        if (belief1.state === 'treasure_belief' && belief2.state === 'treasure_belief') {
            return belief1.goldDir !== belief2.goldDir;
        }

        return false;
    }

    /**
     * Helper: Get target position based on belief
     */
    _getTargetFromBelief(belief, preference, goldPos, rocksPos) {
        if (!belief || belief.state === 'no_belief') {
            // If no belief, just go to gold (actual position)
            return goldPos;
        }

        // Based on belief, determine where farmer thinks gold is
        // If belief says left, target is position 0, if right, target is position 18
        return belief.goldDir === 'left' ? 0 : 10;
    }

}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BeliefTrialGenerator;
}
