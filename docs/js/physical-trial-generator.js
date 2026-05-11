/**
 * Trial Generator
 * Creates trial data based on high-level parameters.
 */
class TrialGenerator {
    constructor(config = {}) {
        this.config = {
            farmerStartPos: 9,
            wizardPos: 9,
            applePos: 18,
            bananaPos: 0,
            rockPos: 14,
            wizardTriggerPos: {
                toApple: 13,
                toBanana: 5,
            },
            ...config
        };
    }

    /**
     * Creates a sequence of frames for an agent moving from a start to an end position.
     * @param {number} startPos - The starting position.
     * @param {number} endPos - The ending position.
     * @param {Array} baseEntities - The static entities to include in each frame.
     * @param {string} wizardAction - The action the wizard will take.
     * @param {boolean} rockStartsPresent - Whether rock is initially present.
     * @param {boolean} showThoughtBubbles - Whether to show thought bubbles (only for initial movement).
     * @returns {Array} An array of frame objects.
     */
    _generateMoveFrames(startPos, endPos, baseEntities, wizardAction, rockStartsPresent, showThoughtBubbles = true) {
        const frames = [];
        let currentPos = startPos;
        const step = endPos > startPos ? 1 : -1;

        // Create a copy of entities to avoid modifying the original array
        const staticEntities = baseEntities.filter(e => e.type !== 'farmer');

        while (currentPos !== endPos) {
            currentPos += step;
            const frameEntities = [
                ...staticEntities,
                { type: 'farmer', position: currentPos, highlighted: true }
            ];

            // Add thought bubbles only for initial farmer movement (before wizard acts)
            let thoughtBubbles = null;
            if (showThoughtBubbles) {
                const frameNumber = Math.abs(currentPos - startPos); // Frame number in movement sequence
                
                // Only show thought bubbles during initial farmer movement (before wizard acts)
                if (frameNumber <= 4) {
                    thoughtBubbles = this._generateThoughtBubbles(wizardAction, rockStartsPresent, frameNumber, frameNumber >= 3);
                }
            }

            // Show wizard with wand raised starting from frame 3 (when decision is made)
            let adjustedEntities = frameEntities;
            if (showThoughtBubbles) {
                const frameNumber = Math.abs(currentPos - startPos);
                if (frameNumber >= 3) {
                    adjustedEntities = frameEntities.map(e => {
                        if (e.type === 'wizard') {
                            return { ...e, withWand: true, highlighted: true };
                        }
                        return e;
                    });
                }
            }

            frames.push({
                entities: adjustedEntities,
                action: { type: 'farmer_moves', position: currentPos },
                description: `Farmer moves to position ${currentPos}`,
                thoughtBubbles: thoughtBubbles
            });
        }
        return frames;
    }

    /**
     * Generates thought bubbles for the wizard's decision-making process.
     * @param {string} wizardAction - The action the wizard will take.
     * @param {boolean} rockStartsPresent - Whether rock is initially present.
     * @param {number} frameNumber - Current frame number in the sequence.
     * @param {boolean} keepDecidedBubble - Whether to keep showing the decided bubble after decision.
     * @returns {Object} Thought bubble configuration.
     */
    _generateThoughtBubbles(wizardAction, rockStartsPresent, frameNumber, keepDecidedBubble = false) {
        // Determine the two choices: do nothing vs take action
        const doNothingBubble = { state: 'empty', position: this.config.rockPos };
        
        // The action bubble depends on what the wizard COULD do based on current state
        let takeActionBubble;
        if (rockStartsPresent) {
            // If rock is present, wizard could remove it
            takeActionBubble = { state: 'rock-with-cross', position: this.config.rockPos };
        } else {
            // If no rock is present, wizard could place one
            takeActionBubble = { state: 'rock', position: this.config.rockPos };
        }
        
        // For frames 1-2: Show both thought bubbles (do nothing vs take action)
        if (frameNumber <= 2) {
            return {
                left: doNothingBubble,
                right: takeActionBubble
            };
        }
        // For frames 3+ or when keepDecidedBubble is true: Show only the decided thought bubble
        else if (frameNumber >= 3 || keepDecidedBubble) {
            if (wizardAction === 'nothing') {
                return { left: doNothingBubble };
            } else {
                return { right: takeActionBubble };
            }
        }
        
        return null;
    }

    /**
     * Generates the sequence of frames for the wizard's action.
     * @param {string} actionType - 'place_rock', 'remove_rock', or 'nothing'.
     * @param {Array} baseEntities - The entities present when the wizard acts.
     * @param {boolean} instructionOnly - Whether this is for instruction purposes.
     * @returns {Array} An array of frame objects for the wizard's action.
     */
    _generateWizardActionFrames(actionType, baseEntities, instructionOnly = false) {
        if (actionType === 'nothing') {
            if (instructionOnly) {
                // For instruction demos, show wizard waving wand but doing nothing
                const frames = [];
                const rockInitiallyPresent = baseEntities.some(e => e.type === 'rock');
                const finalThoughtBubble = this._generateThoughtBubbles(actionType, rockInitiallyPresent, 5, true);
                
                // 1. Wave wand
                frames.push({
                    entities: baseEntities.map(e => e.type === 'wizard' ? { ...e, highlighted: true } : e),
                    action: { type: 'wave_wand', position: this.config.rockPos },
                    description: 'Wizard waves wand',
                    thoughtBubbles: finalThoughtBubble
                });
                
                // 2. Wizard with wand raised (but no lightning)
                const wandEntities = baseEntities.map(e => {
                    if (e.type === 'wizard') return { ...e, highlighted: true, withWand: true };
                    return e;
                });
                frames.push({
                    entities: wandEntities,
                    action: { type: 'wizard_nothing', position: this.config.wizardPos },
                    description: 'Wizard holds wand up but nothing happens',
                    thoughtBubbles: finalThoughtBubble
                });
                
                // 3. Wizard returns to normal
                frames.push({
                    entities: baseEntities.map(e => ({...e, highlighted: false })),
                    action: null,
                    description: 'Wizard lowers wand, nothing has changed',
                    thoughtBubbles: finalThoughtBubble
                });
                
                return frames;
            } else {
                // Wizard does nothing - but still lowers wand to show action is complete
                const rockWasPresent = baseEntities.some(e => e.type === 'rock');
                const nothingThoughtBubble = this._generateThoughtBubbles('nothing', rockWasPresent, 5, true);
                
                // Return wizard to normal state (without wand) to match other actions
                const normalEntities = baseEntities.map(e => {
                    if (e.type === 'wizard') return { ...e, withWand: false, highlighted: false };
                    return e;
                });
                
                return [{
                    entities: normalEntities,
                    action: { type: 'wizard_nothing', position: this.config.wizardPos },
                    description: 'Wizard does nothing and lowers wand',
                    thoughtBubbles: nothingThoughtBubble
                }];
            }
        }

        const rockIsPresent = baseEntities.some(e => e.type === 'rock');
        const frames = [];

        // Determine initial rock state for thought bubbles
        const rockWasPresentInitially = baseEntities.some(e => e.type === 'rock');
        const finalDecidedThoughtBubble = this._generateThoughtBubbles(actionType, rockWasPresentInitially, 5, true);

        // 1. Wizard raises wand and lightning happens
        const wandRaisedEntities = baseEntities.map(e => {
            if (e.type === 'wizard') return { ...e, highlighted: true, withWand: true };
            return e;
        });

        // 2. Lightning effect
        const lightningEntities = baseEntities.map(e => {
            if (e.type === 'wizard') return { ...e, highlighted: true, withWand: true };
            if (e.type === 'rock') return { ...e, highlighted: true }; 
            return e;
        });
        frames.push({
            entities: lightningEntities,
            action: { type: 'lightning_effect', position: this.config.rockPos },
            description: 'Wizard raises wand with magical effect',
            thoughtBubbles: finalDecidedThoughtBubble
        });

        // 3. Rock appears or disappears
        let finalEntities = baseEntities.filter(e => e.type !== 'wizard'); // Wizard returns to normal
        finalEntities.push({ type: 'wizard', position: this.config.wizardPos });

        if (actionType === 'place_rock') {
            finalEntities.push({ type: 'rock', position: this.config.rockPos, highlighted: true });
        } else { // remove_rock
            finalEntities = finalEntities.filter(e => e.type !== 'rock');
        }

        frames.push({
            entities: finalEntities,
            action: { type: actionType, position: this.config.rockPos },
            description: `Rock ${actionType === 'place_rock' ? 'appears' : 'disappears'}`,
            thoughtBubbles: finalDecidedThoughtBubble
        });
        
        // 4. Quiescent state after rock action
        frames.push({
            entities: finalEntities.map(e => ({...e, highlighted: false })),
            action: null,
            description: `Path to apple is now ${actionType === 'place_rock' ? 'blocked' : 'clear'}`,
            thoughtBubbles: finalDecidedThoughtBubble
        });

        return frames;
    }
    
    /**
     * Generates a complete trial object from high-level parameters.
     */
    generateTrial({ id, label, description, initialDirectionGoal, wizardAction, rockStartsPresent, finalOutcome, instructionOnly }) {
        let frames = [];
        let currentEntities = [
            { type: 'farmer', position: this.config.farmerStartPos },
            { type: 'wizard', position: this.config.wizardPos },
            { type: 'apple', position: this.config.applePos },
            { type: 'banana', position: this.config.bananaPos },
        ];
        if (rockStartsPresent) {
            currentEntities.push({ type: 'rock', position: this.config.rockPos });
        }
        
        // Frame Generation
        // 1. Initial Frame (with thought bubbles for all trials now)
        let initialThoughtBubbles = this._generateThoughtBubbles(wizardAction, rockStartsPresent, 1);
        
        frames.push({ 
            entities: [...currentEntities], 
            action: null, 
            description: 'Initial state',
            thoughtBubbles: initialThoughtBubbles 
        });

        if (instructionOnly) {
            // For instruction-only trials, show the thought bubble progression first
            // 2. Second frame showing both thought bubbles
            frames.push({
                entities: [...currentEntities],
                action: null,
                description: 'Wizard considers options',
                thoughtBubbles: this._generateThoughtBubbles(wizardAction, rockStartsPresent, 2)
            });
            
            // 3. Third frame showing decided thought bubble
            frames.push({
                entities: currentEntities.map(e => e.type === 'wizard' ? { ...e, withWand: true, highlighted: true } : e),
                action: null,
                description: 'Wizard decides',
                thoughtBubbles: this._generateThoughtBubbles(wizardAction, rockStartsPresent, 3)
            });
            
            // 4. Wizard's Action (farmer stays stationary)
            const wizardFrames = this._generateWizardActionFrames(wizardAction, currentEntities, instructionOnly);
            frames.push(...wizardFrames);
        } else {
            // Regular trial with farmer movement
            // 2. Farmer's first move (towards initial goal) - with thought bubbles
            const triggerPos = initialDirectionGoal === 'apple' ? this.config.wizardTriggerPos.toApple : this.config.wizardTriggerPos.toBanana;
            const firstMoveFrames = this._generateMoveFrames(this.config.farmerStartPos, triggerPos, currentEntities, wizardAction, rockStartsPresent, true);
            frames.push(...firstMoveFrames);

            // Get the state right before the wizard acts
            let stateBeforeWizard = frames[frames.length - 1].entities;
            
            // 3. Wizard's Action
            const wizardFrames = this._generateWizardActionFrames(wizardAction, stateBeforeWizard, false);
            frames.push(...wizardFrames);
            
            // Get the state right after the wizard acts
            let stateAfterWizard = frames[frames.length - 1].entities;
            let farmerPosAfterWizard = stateAfterWizard.find(e => e.type === 'farmer').position;

            // 4. Farmer's final move (towards final outcome) - keep decided thought bubble
            const finalTargetPos = finalOutcome === 'apple' ? this.config.applePos : this.config.bananaPos;
            const decidedThoughtBubble = this._generateThoughtBubbles(wizardAction, rockStartsPresent, 5, true);
            
            // Generate final move frames manually to add thought bubbles
            let currentPos = farmerPosAfterWizard;
            const step = finalTargetPos > currentPos ? 1 : -1;
            const staticEntities = stateAfterWizard.filter(e => e.type !== 'farmer');

            while (currentPos !== finalTargetPos) {
                currentPos += step;
                const frameEntities = [
                    ...staticEntities,
                    { type: 'farmer', position: currentPos, highlighted: true }
                ];

                frames.push({
                    entities: frameEntities,
                    action: { type: 'farmer_moves', position: currentPos },
                    description: `Farmer moves to position ${currentPos}`,
                    thoughtBubbles: decidedThoughtBubble
                });
            }
            
            // 5. Final "reaches" frame
            let finalFrameState = frames[frames.length - 1].entities;
            frames.push({
                entities: finalFrameState.map(e => e.type === 'farmer' ? { ...e, highlighted: true } : e),
                action: { type: 'farmer_reaches', position: finalTargetPos },
                description: `Farmer reaches ${finalOutcome}`,
                thoughtBubbles: decidedThoughtBubble
            });
        }

        return { id, label, description, outcome: `the ${finalOutcome}`, frames };
    }
}