/**
 * Preference Trial Generator
 * Creates trial data for preference intervention experiments.
 */
class PreferenceTrialGenerator {
    constructor(config = {}) {
        this.config = {
            farmerStartPos: 5,
            wizardPos: 5,
            laneLength: 11,
            wizardTriggerPos: 7,
            ...config
        };
    }

    /**
     * Calculates utility of a basket given contents and preferences
     */
    calculateUtility(contents, preference) {
        const bananas = contents.bananas || 0;
        const apples = contents.apples || 0;
        return (bananas * preference.banana) + (apples * preference.apple);
    }

    /**
     * Generates a preference trial based on provided parameters
     */
    generateTrial(trial) {
        const {
            id,
            initialConfig,
            initialDirection,
            wizardAction,
            farmerPreference
        } = trial;

        const farmerStartPos = this.config.farmerStartPos;
        const highlightPositions = [farmerStartPos - 2, farmerStartPos + 2];

        let frames = [];

        // 1. Setup Initial Entities
        let leftBasket = {
            type: 'basket',
            side: 'left',
            position: 0,
            contents: { ...initialConfig.left }
        };
        let rightBasket = {
            type: 'basket',
            side: 'right',
            position: 10,
            contents: { ...initialConfig.right }
        };



        let currentEntities = [
            { type: 'farmer', position: farmerStartPos, direction: initialDirection },
            { type: 'wizard', position: this.config.wizardPos, withWand: false },
            leftBasket,
            rightBasket
        ];

        // 2. Initial Thought Bubbles
        let wizardBubbles = {
            left: { action: 'add_apple_left' },
            middle: { action: 'do_nothing' },
            right: { action: 'add_apple_right' }
        };

        const numberToWord = (n) => {
            if (n === 1) return '1';
            if (n === 2) return '2';
            if (n === 3) return '3';
            return n;
        };

        const getContentsString = (contents) => {
            let parts = [];
            if (contents.bananas > 0) parts.push(`${numberToWord(contents.bananas)} ${contents.bananas === 1 ? 'banana' : 'bananas'}`);
            if (contents.apples > 0) parts.push(`${numberToWord(contents.apples)} ${contents.apples === 1 ? 'apple' : 'apples'}`);
            return parts.join(' and ');
        };

        const leftStr = getContentsString(initialConfig.left);
        const rightStr = getContentsString(initialConfig.right);

        const leftCount = (initialConfig.left.bananas || 0) + (initialConfig.left.apples || 0);
        // rightCount unused but could be nice for completeness
        // const rightCount = (initialConfig.right.bananas || 0) + (initialConfig.right.apples || 0);

        const leftVerb = leftCount === 1 ? 'is' : 'are';

        const basketDesc = `There ${leftVerb} ${leftStr} in the left basket and ${rightStr} in the right basket.`;
        const initialDesc = `${basketDesc}\nThe wizard looks at what's happening.`;

        // Calculate intervention position: 2 steps from start in initial direction
        const initDirVal = initialDirection === 'left' ? -1 : 1;
        // interventionPos unused in highlighting now, but keeping var for logic if needed
        const interventionPos = farmerStartPos + (2 * initDirVal);

        frames.push({
            entities: JSON.parse(JSON.stringify(currentEntities)),
            thoughtBubbles: { wizard: wizardBubbles },
            description: initialDesc,
            highlightPositions: highlightPositions,
            duration: 1000
        });

        // 3. Farmer Moves Initially (2 steps)
        for (let i = 1; i <= 2; i++) {
            let newPos = farmerStartPos + (i * initDirVal);
            currentEntities = currentEntities.map(e =>
                e.type === 'farmer' ? { ...e, position: newPos } : e
            );

            frames.push({
                entities: JSON.parse(JSON.stringify(currentEntities)),
                thoughtBubbles: { wizard: wizardBubbles },
                description: initialDesc,
                highlightPositions: highlightPositions,
                duration: 800
            });
        }
        let currentPos = farmerStartPos + (2 * initDirVal);

        // 4. Wizard Action
        let actingBubbles = {};
        let decisionDesc = "";

        if (wizardAction.type === 'add_apple') {
            if (wizardAction.side === 'left') {
                actingBubbles = { left: { action: 'add_apple_left', highlight: true } };
                decisionDesc = "The wizard decides to add an apple to the left basket.";
            } else {
                actingBubbles = { right: { action: 'add_apple_right', highlight: true } };
                decisionDesc = "The wizard decides to add an apple to the right basket.";
            }

            // Raise wand before showing the chosen bubble 
            currentEntities = currentEntities.map(e =>
                e.type === 'wizard' ? { ...e, withWand: true } : e
            );

        } else {
            actingBubbles = { middle: { action: 'do_nothing', highlight: true } };
            decisionDesc = "The wizard decides to do nothing.";
        }

        // Decision Frame (Chosen Bubble Stays)
        frames.push({
            entities: JSON.parse(JSON.stringify(currentEntities)),
            thoughtBubbles: { wizard: actingBubbles },
            description: decisionDesc,
            highlightPositions: highlightPositions,
            duration: 1000
        });

        let revealBubbles = null;

        if (wizardAction.type === 'add_apple') {
            if (wizardAction.side === 'left') {
                revealBubbles = { left: { action: 'add_apple_left', noBubble: true } };
            } else {
                revealBubbles = { right: { action: 'add_apple_right', noBubble: true } };
            }
        } else {

            // If doing nothing, bubble disappears entirely (null)
            revealBubbles = null;
        }

        // Store persistent bubbles
        const finalWizardBubbles = revealBubbles;

        frames.push({
            entities: JSON.parse(JSON.stringify(currentEntities)),
            thoughtBubbles: { wizard: actingBubbles }, // Keep acting bubbles (full) here
            description: decisionDesc,
            highlightPositions: highlightPositions,
            duration: 1000
        });


        if (wizardAction.type === 'add_apple') {

            let targetPos = wizardAction.side === 'left' ? 0 : 10;

            // Lightning Frame
            frames.push({
                entities: JSON.parse(JSON.stringify(currentEntities)),
                action: {
                    type: 'wizard_action',
                    subType: 'add_apple',
                    targetPosition: targetPos
                },
                thoughtBubbles: { wizard: actingBubbles }, // Keep acting bubbles (full) during action
                description: decisionDesc,
                highlightPositions: highlightPositions
            });

            // Update Basket
            currentEntities = currentEntities.map(e => {
                if (e.type === 'basket' && e.side === wizardAction.side) {
                    let newContents = { ...e.contents };
                    newContents.apples = (newContents.apples || 0) + 1;
                    return { ...e, contents: newContents };
                }
                if (e.type === 'wizard') return { ...e, withWand: false };
                return e;
            });

            // Post-Action Frame (Fruits Changed) - Bubble background disappears here
            frames.push({
                entities: JSON.parse(JSON.stringify(currentEntities)),
                thoughtBubbles: { wizard: finalWizardBubbles }, // Now use final bubbles (no background)
                description: decisionDesc,
                highlightPositions: highlightPositions,
                duration: 1000
            });

            // Wait Frame
            frames.push({
                entities: JSON.parse(JSON.stringify(currentEntities)),
                thoughtBubbles: { wizard: finalWizardBubbles },
                description: decisionDesc,
                highlightPositions: highlightPositions,
                duration: 1000
            });
        } else {
            // Nothing Action - already handled above with null bubbles
            currentEntities = currentEntities.map(e =>
                e.type === 'wizard' ? { ...e, withWand: false } : e
            );

            frames.push({
                entities: JSON.parse(JSON.stringify(currentEntities)),
                thoughtBubbles: { wizard: finalWizardBubbles },
                description: decisionDesc,
                highlightPositions: highlightPositions,
                duration: 1000
            });

            // Wait Frame
            frames.push({
                entities: JSON.parse(JSON.stringify(currentEntities)),
                thoughtBubbles: { wizard: finalWizardBubbles },
                description: decisionDesc,
                highlightPositions: highlightPositions,
                duration: 1000
            });
        }

        // 5. Final Decision & Move
        const finalLeftBasket = currentEntities.find(e => e.type === 'basket' && e.side === 'left');
        const finalRightBasket = currentEntities.find(e => e.type === 'basket' && e.side === 'right');

        const finalULeft = this.calculateUtility(finalLeftBasket.contents, farmerPreference);
        const finalURight = this.calculateUtility(finalRightBasket.contents, farmerPreference);

        let finalDirection = initialDirection;
        if (finalULeft > finalURight) finalDirection = 'left';
        else if (finalURight > finalULeft) finalDirection = 'right';

        const finalTargetPos = finalDirection === 'left' ? 1 : 9;

        // Animate walk to target
        while (currentPos !== finalTargetPos) {
            if (currentPos < finalTargetPos) currentPos++;
            else currentPos--;

            currentEntities = currentEntities.map(e =>
                e.type === 'farmer' ? { ...e, position: currentPos, direction: finalDirection } : e
            );

            frames.push({
                entities: JSON.parse(JSON.stringify(currentEntities)),
                thoughtBubbles: { wizard: finalWizardBubbles },
                description: decisionDesc,
                highlightPositions: highlightPositions,
                duration: 800
            });
        }

        // Final Frame
        frames.push({
            entities: JSON.parse(JSON.stringify(currentEntities)),
            thoughtBubbles: { wizard: finalWizardBubbles },
            description: decisionDesc,
            highlightPositions: highlightPositions,
            duration: 1000
        });

        return {
            id,
            frames
        };
    }
}
