/**
 * Grid World Renderer for Belief Trials
 * A streamlined renderer focusing on the belief domain experiments.
 */
class BeliefGridWorldRenderer {
    constructor(canvas, config = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        const pixelRatio = window.devicePixelRatio || 1;

        this.config = {
            laneLength: 11,
            maxWidth: 900,
            laneHeight: 100,
            laneColor: '#ddd',
            animationSpeed: 700,
            horizontalBorder: 80,
            verticalBorder: 20,
            pixelRatio: pixelRatio,
            imageBasePath: 'images',
            ...config
        };

        // Calculate cell size and scale factor
        this.config.cellSize = Math.floor((this.config.maxWidth - 2 * this.config.horizontalBorder) / this.config.laneLength);
        this.config.scaleFactor = this.config.maxWidth / 1000;

        const displayWidth = this.config.laneLength * this.config.cellSize + 2 * this.config.horizontalBorder + 200;
        const displayHeight = this.config.laneHeight + Math.round(320 * this.config.scaleFactor) + this.config.verticalBorder;

        this.canvas.style.width = `${displayWidth}px`;
        this.canvas.style.height = `${displayHeight}px`;
        this.canvas.width = displayWidth * pixelRatio;
        this.canvas.height = displayHeight * pixelRatio;

        this.ctx.scale(pixelRatio, pixelRatio);
        this.ctx.imageSmoothingEnabled = true;
        this.ctx.imageSmoothingQuality = 'high';

        this.displayWidth = displayWidth;
        this.displayHeight = displayHeight;

        // Animation state
        this.animationFrame = null;
        this.isAnimating = false;

        // Image cache
        this.images = new Map();
        this.loadImages();
    }

    loadImages() {
        const basePath = this.config.imageBasePath;
        const imageFiles = {
            farmer: `${basePath}/farmer.png`,
            wizard: `${basePath}/wizard.png`,
            'wizard-wand': `${basePath}/wizard-wand.png`,
            lightning: `${basePath}/lightning.png`,
            'treasure-closed': `${basePath}/treasure-closed.png`,
            'treasure-gold': `${basePath}/treasure-gold.png`,
            'treasure-rocks': `${basePath}/treasure-rocks.png`,
            thought: `${basePath}/thought.png`,
            'thought-middle': `${basePath}/thought-middle.png`,
            'signpost-left': `${basePath}/signpost-left.png`,
            'signpost-right': `${basePath}/signpost-right.png`
        };

        Object.entries(imageFiles).forEach(([name, src]) => {
            const img = new Image();
            img.onload = () => this.images.set(name, img);
            img.onerror = () => console.warn(`Failed to load image: ${src}`);
            img.src = src;
        });
    }

    drawWizardBubbleContent(x, y, action, flip, scaleFactor) {
        if (flip) {
            this.ctx.scale(-1, 1);
            x = -x;
        }

        if (action === 'point_left') {
            const img = this.images.get('signpost-left');
            if (img && img.complete) {
                const size = 40 * scaleFactor;
                this.ctx.drawImage(img, x - size / 2, y - size / 2, size, size);
            }
        } else if (action === 'point_right') {
            const img = this.images.get('signpost-right');
            if (img && img.complete) {
                const size = 40 * scaleFactor;
                this.ctx.drawImage(img, x - size / 2, y - size / 2, size, size);
            }
        } else if (action === 'do_nothing') {
            // Empty bubble for do nothing
        }
    }

    drawLane(scene, frameIndex) {
        const { laneLength, cellSize, laneHeight, laneColor, verticalBorder, scaleFactor } = this.config;

        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

        const laneWidth = laneLength * cellSize;
        const laneX = (this.displayWidth - laneWidth) / 2;
        const laneY = verticalBorder + Math.round(100 * scaleFactor);

        this.ctx.strokeStyle = laneColor;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(laneX, laneY, laneWidth, laneHeight - 20);

        this.ctx.lineWidth = 1;
        for (let i = 1; i < laneLength; i++) {
            const dividerX = laneX + i * cellSize;
            this.ctx.beginPath();
            this.ctx.moveTo(dividerX, laneY);
            this.ctx.lineTo(dividerX, laneY + laneHeight - 20);
            this.ctx.stroke();
        }

        this.laneX = laneX;
    }

    drawEntity(entity) {
        if (entity.type === 'wizard') return;

        const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
        const laneY = verticalBorder + Math.round(100 * scaleFactor);
        const x = this.laneX + entity.position * cellSize;
        const y = laneY + 5;

        // Determine which image to use for chest entities
        let imageKey = entity.type;
        if (entity.type === 'chest-left' || entity.type === 'chest-right') {
            if (entity.opened && entity.contents) {
                imageKey = entity.contents === 'gold' ? 'treasure-gold' : 'treasure-rocks';
            } else {
                imageKey = 'treasure-closed';
            }
        }

        const image = this.images.get(imageKey);
        if (image && image.complete) {
            const imgSize = Math.min(cellSize - 10, laneHeight - 30);
            const imgX = Math.round(x + (cellSize - imgSize) / 2);
            const imgY = Math.round(y + (laneHeight - 30 - imgSize) / 2);

            this.ctx.save();
            this.ctx.imageSmoothingEnabled = true;
            this.ctx.imageSmoothingQuality = 'high';
            this.ctx.drawImage(image, imgX, imgY, imgSize, imgSize);
            this.ctx.restore();
        }
    }

    renderFrame(scene, frameIndex = 0) {
        this.drawLane(scene, frameIndex);
        if (!scene || !scene.frames || frameIndex >= scene.frames.length) return;

        const frame = scene.frames[frameIndex];

        // Draw entities: chests first, then farmer on top
        const entitiesToDraw = [
            ...frame.entities.filter(e => e.type === 'chest-left' || e.type === 'chest-right'),
            ...frame.entities.filter(e => e.type === 'farmer')
        ];
        entitiesToDraw.forEach(entity => this.drawEntity(entity));

        if (frame.action) {
            this.drawActionIndicator(frame.action);
        }

        const wizard = frame.entities.find(e => e.type === 'wizard');
        if (wizard) {
            this.drawWizard(wizard);
        }

        if (frame.thoughtBubbles) {
            if (frame.thoughtBubbles.farmer) {
                const farmer = frame.entities.find(e => e.type === 'farmer');
                if (farmer) {
                    this.drawFarmerThoughtBubble(farmer.position, frame.thoughtBubbles.farmer);
                }
            }
            if (frame.thoughtBubbles.wizard) {
                const wizard = frame.entities.find(e => e.type === 'wizard');
                if (wizard) {
                    this.drawWizardThoughtBubbles(wizard.position, frame.thoughtBubbles.wizard);
                }
            }
        }

        // Draw descriptive text
        this.drawDescriptiveText(frame, frameIndex, scene);
    }

    drawActionIndicator(action) { }

    drawDescriptiveText(frame, frameIndex, scene) {
        const text = this.getDescriptiveText(frame, frameIndex, scene);
        if (!text) return;

        const { laneHeight, verticalBorder, scaleFactor } = this.config;
        // Start a bit higher to accommodate multiple lines
        const textY = verticalBorder + laneHeight + 300 * scaleFactor;
        const textX = this.displayWidth / 2;
        const fontSize = Math.round(14 + 2 * scaleFactor);
        const lineHeight = fontSize * 1.2;

        // Split text into lines
        const lines = text.split('\n');

        this.ctx.fillStyle = '#ffffff';
        // Clear a larger area based on number of lines
        const totalHeight = lines.length * lineHeight;
        this.ctx.fillRect(0, textY - 15, this.displayWidth, totalHeight + 40);

        this.ctx.fillStyle = '#666666';
        this.ctx.font = `italic ${fontSize}px Arial, sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';

        lines.forEach((line, index) => {
            this.ctx.fillText(line, textX, textY + (index * lineHeight));
        });
    }

    getDescriptiveText(frame, frameIndex, scene) {
        // 1. Get Farmer Text
        let farmerText = null;
        try {
            farmerText = this.getFarmerText(frame, frameIndex, scene);
        } catch (e) {
            console.error("Error getting farmer text:", e);
        }

        // 2. Get Wizard Text
        let wizardText = "";
        const wizardBubbles = frame.thoughtBubbles && frame.thoughtBubbles.wizard;

        if (wizardBubbles) {
            const keys = Object.keys(wizardBubbles);
            const hasDecided = keys.length === 1;

            if (hasDecided) {
                const actionText = this.getWizardActionText(wizardBubbles);
                wizardText = `The wizard decides to ${actionText}`;
            }
        }

        // 3. Arbitration for "One Line" rule
        const description = frame.description || "";

        // Case A: Wizard Action/Decision explicitly mentioned
        if (description.startsWith("The wizard decides")) {
            return description;
        }
        // Case B: Initial Phase (Before Wizard Action)
        if ((description.includes("The wizard looks") || description.includes("The wizard considers")) && farmerText) {
            return farmerText;
        }

        // Case C: Farmer Action/Update explicitly mentioned or Passive frames
        if (farmerText) {
            return farmerText;
        }

        // Fallback
        return wizardText;
    }

    getWizardActionText(wizardBubbles) {
        if (wizardBubbles.left) {
            return "show that the gold is to the left.";
        } else if (wizardBubbles.right) {
            return "show that the gold is to the right.";
        } else if (wizardBubbles.middle) {
            return "do nothing.";
        }
        return "do nothing.";
    }

    getWizardSignDirection(frame) {
        // Check current frame bubbles
        const wizardBubbles = frame.thoughtBubbles?.wizard;
        if (wizardBubbles) {
            if (wizardBubbles.left && (wizardBubbles.left.action === 'point_left' || wizardBubbles.left.action === 'show_signpost')) return 'left';
            if (wizardBubbles.right && (wizardBubbles.right.action === 'point_right' || wizardBubbles.right.action === 'show_signpost')) return 'right';
        }
        return null;
    }

    getFarmerText(frame, frameIndex, scene) {
        // Special case overrides based on frame description from generator
        if (frame.description === 'Farmer considers wizard suggestion') {
            return "";
        }
        // Support new persistent description text
        if (frame.description && frame.description.startsWith('The farmer ignores the wizard')) {
            return frame.description;
        }
        if (frame.description === 'The farmer considers the sign.') {
            const signDir = this.getWizardSignDirection(frame);

            if (signDir) {
                // In the No Belief -> Ignore sequence, the farmer chooses the opposite of the sign
                const farmerBeliefDir = signDir === 'left' ? 'right' : 'left';
                return `The farmer ignores the wizard and goes to the ${farmerBeliefDir}.`;
            }

            return "The farmer ignores the wizard.";
        }

        const farmerBubbles = frame.thoughtBubbles?.farmer;

        // 1. Check for belief update (Reaction State)
        if (farmerBubbles && farmerBubbles.updated) {
            // Determine active belief
            const activeBelief = (farmerBubbles.initial && farmerBubbles.initial.chosen)
                ? farmerBubbles.initial
                : farmerBubbles.updated;

            // Get direction, with strict checks
            const beliefDir = activeBelief?.goldDir;

            // If valid belief direction is found, generate text
            if (beliefDir) {
                const beliefText = beliefDir === 'left' ? 'left' : 'right';

                // Check for wizard signpost action from bubbles
                const signDir = this.getWizardSignDirection(frame);

                if (signDir) {
                    if (beliefDir === signDir) {
                        return `The farmer believes the wizard and goes to the ${beliefText}.`;
                    } else {
                        return `The farmer ignores the wizard and goes to the ${beliefText}.`;
                    }
                }

                // Default if no signpost (e.g. Wizard Does Nothing)
                return `The farmer goes to the ${beliefText}.`;
            }
        }

        // 2. Check for single/initial belief (Initial State)
        if (farmerBubbles) {
            const bubble = farmerBubbles.state ? farmerBubbles : farmerBubbles.initial;
            if (bubble) {
                if (bubble.state === 'no_belief') {
                    return "The farmer does not know where the gold is.";
                }
                if (bubble.state === 'treasure_belief' || bubble.goldDir) {
                    const dir = bubble.goldDir === 'left' ? 'left' : 'right';
                    if (dir) return `The farmer thinks the gold is to the ${dir}.`;
                }
            }
        }

        return null;
    }

    drawWizard(wizard) {
        const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
        const imageKey = wizard.withWand ? 'wizard-wand' : 'wizard';
        const image = this.images.get(imageKey);

        if (image) {
            const wizardSize = Math.round(75 * scaleFactor);
            const x = Math.round(this.laneX + wizard.position * cellSize + (cellSize - wizardSize) / 2);
            const laneY = verticalBorder + Math.round(100 * scaleFactor);
            const y = Math.round(laneY + laneHeight + 100 * scaleFactor);

            this.ctx.save();
            this.ctx.imageSmoothingEnabled = true;
            this.ctx.imageSmoothingQuality = 'high';
            this.ctx.drawImage(image, x, y, wizardSize, wizardSize);
            this.ctx.restore();
        }
    }


    playAnimation(scene, options = {}) {
        if (this.isAnimating) this.stopAnimation();

        this.isAnimating = true;
        let frameIndex = 0;
        let lastFrameTime = 0;
        let loopCount = 0;
        const { loop = false, loopDelay = 0, onFrameChange = null, onComplete = null, speed = this.config.animationSpeed } = options;

        const animate = (timestamp) => {
            if (!this.isAnimating) return;

            // Determine duration for current frame
            const currentFrame = scene.frames[frameIndex];
            const currentDuration = (currentFrame && currentFrame.duration) ? currentFrame.duration : speed;

            if (timestamp - lastFrameTime >= currentDuration) {
                lastFrameTime = timestamp;

                this.renderFrame(scene, frameIndex);
                if (onFrameChange) onFrameChange(frameIndex);

                frameIndex++;

                if (loop && frameIndex === 1 && loopCount > 0 && loopDelay > 0) {
                    lastFrameTime += loopDelay;
                }

                if (frameIndex >= scene.frames.length) {
                    if (loop) {
                        frameIndex = 0;
                        loopCount++;
                    } else {
                        this.isAnimating = false;
                        if (onComplete) onComplete();
                        return;
                    }
                }
            }
            this.animationFrame = requestAnimationFrame(animate);
        };

        this.animationFrame = requestAnimationFrame(animate);
    }

    stopAnimation() {
        this.isAnimating = false;
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }

    drawFarmerThoughtBubble(farmerPosition, bubbleContent) {
        const { cellSize, verticalBorder, scaleFactor } = this.config;
        const farmerX = this.laneX + farmerPosition * cellSize + cellSize / 2;
        const laneY = verticalBorder + Math.round(100 * scaleFactor);
        const farmerY = laneY - Math.round(50 * scaleFactor);

        const drawBubble = (content, x, flip, alpha, type = 'normal') => {
            if (content) {
                const yOffset = type === 'middle' ? -20 * scaleFactor : 10 * scaleFactor;
                this.drawSingleFarmerThoughtBubble(x, farmerY + yOffset, content, flip, alpha, type);
            }
        };

        if (bubbleContent.left || bubbleContent.middle || bubbleContent.right) {
            // New 3-bubble layout support
            if (bubbleContent.left) {
                const alpha = bubbleContent.left.alpha !== undefined ? bubbleContent.left.alpha : 1.0;
                drawBubble(bubbleContent.left, farmerX - 105 * scaleFactor, true, alpha, 'normal');
            }
            if (bubbleContent.middle) {
                const alpha = bubbleContent.middle.alpha !== undefined ? bubbleContent.middle.alpha : 1.0;
                drawBubble(bubbleContent.middle, farmerX, false, alpha, 'middle');
            }
            if (bubbleContent.right) {
                const alpha = bubbleContent.right.alpha !== undefined ? bubbleContent.right.alpha : 1.0;
                drawBubble(bubbleContent.right, farmerX + 105 * scaleFactor, false, alpha, 'normal');
            }

        } else if (bubbleContent.initial && bubbleContent.updated) {
            // Check if initial belief is chosen (farmer ignores wizard)
            const initialChosen = bubbleContent.initial.chosen;
            // Check if this is a correction (old deception detection logic)
            const isCorrection = bubbleContent.initial.corrected;

            // Determine opacity based on which belief is chosen/active
            let initialAlpha, updatedAlpha;

            // Check for explicit alpha overrides in content
            if (typeof bubbleContent.initial.alpha !== 'undefined') initialAlpha = bubbleContent.initial.alpha;
            if (typeof bubbleContent.updated.alpha !== 'undefined') updatedAlpha = bubbleContent.updated.alpha;

            // If not explicit, determine based on state
            if (initialAlpha === undefined || updatedAlpha === undefined) {
                if (initialChosen) {
                    // Farmer ignores wizard: initial is full opacity, updated (wizard's suggestion) is faded
                    if (initialAlpha === undefined) initialAlpha = 1.0;
                    if (updatedAlpha === undefined) updatedAlpha = 0.3;
                } else if (isCorrection) {
                    // Old correction logic
                    if (initialAlpha === undefined) initialAlpha = 1.0;
                    if (updatedAlpha === undefined) updatedAlpha = 0.3;
                } else {
                    // Normal belief change
                    if (initialAlpha === undefined) initialAlpha = 0.3;
                    if (updatedAlpha === undefined) updatedAlpha = 1.0;
                }
            }

            drawBubble(bubbleContent.initial, farmerX - 80 * scaleFactor, true, initialAlpha);
            drawBubble(bubbleContent.updated, farmerX + 80 * scaleFactor, false, updatedAlpha);
        } else {
            drawBubble(bubbleContent.initial, farmerX - 80 * scaleFactor, true, 1.0);
            drawBubble(bubbleContent.updated, farmerX + 80 * scaleFactor, false, 1.0);
            if (bubbleContent.state) {
                drawBubble(bubbleContent, farmerX - 80 * scaleFactor, true, 1.0);
            }
        }
    }

    drawSingleFarmerThoughtBubble(x, y, bubbleContent, flip = false, alpha = 1.0, type = 'normal') {
        let thoughtImage;
        if (type === 'middle') {
            thoughtImage = this.images.get('thought-middle');
        } else {
            thoughtImage = this.images.get('thought');
        }

        if (!thoughtImage || !thoughtImage.complete) return;

        const { scaleFactor } = this.config;
        this.ctx.save();
        this.ctx.globalAlpha = alpha;

        if (flip) {
            this.ctx.scale(-1, 1);
            x = -x;
        }

        let bubbleWidth, bubbleHeight;
        if (type === 'middle') {
            bubbleWidth = 105 * scaleFactor;
            bubbleHeight = 95 * scaleFactor;
        } else {
            bubbleWidth = 125 * scaleFactor;
            bubbleHeight = 75 * scaleFactor;
        }

        if (type === 'middle') {
            this.ctx.drawImage(thoughtImage, x - bubbleWidth / 2.1, y - bubbleHeight / 2.1, bubbleWidth, bubbleHeight);
        } else {
            this.ctx.drawImage(thoughtImage, x - bubbleWidth / 1.8, y - bubbleHeight / 1.8, bubbleWidth, bubbleHeight);
        }

        // Content offset for middle bubble
        const offsetX = type === 'middle' ? 5 * scaleFactor : 0;
        const offsetY = type === 'middle' ? -5 * scaleFactor : 0;

        if (bubbleContent.state === 'treasure_belief') {
            this.drawTreasureBeliefContent(x + offsetX, y + offsetY, bubbleContent, flip, scaleFactor);
        } else if (bubbleContent.state === 'no_belief') {
            this.drawTreasureNoBeliefContent(x + offsetX, y + offsetY, flip, scaleFactor);
        }

        this.ctx.restore();
    }

    drawWizardThoughtBubbles(wizardPosition, bubbles) {
        const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
        const wizardX = this.laneX + wizardPosition * cellSize + cellSize / 2;
        const laneY = verticalBorder + Math.round(100 * scaleFactor);
        // Positioned above the wizard
        const wizardY = laneY + laneHeight + 80 * scaleFactor;

        // Draw left thought bubble (flipped)
        if (bubbles.left) {
            this.drawSingleWizardThoughtBubble(wizardX - 101 * scaleFactor, wizardY + scaleFactor, bubbles.left, 'left');
        }

        // Draw middle thought bubble
        if (bubbles.middle) {
            this.drawSingleWizardThoughtBubble(wizardX, wizardY - 25 * scaleFactor, bubbles.middle, 'middle');
        }

        // Draw right thought bubble
        if (bubbles.right) {
            this.drawSingleWizardThoughtBubble(wizardX + 110 * scaleFactor, wizardY + scaleFactor, bubbles.right, 'right');
        }
    }

    drawSingleWizardThoughtBubble(x, y, bubbleContent, type) {
        const { scaleFactor } = this.config;
        let thoughtImage;
        let flip = false;

        if (type === 'middle') {
            thoughtImage = this.images.get('thought-middle');
        } else {
            thoughtImage = this.images.get('thought');
            if (type === 'left') flip = true;
        }

        if (!thoughtImage || !thoughtImage.complete) return;

        this.ctx.save();

        if (flip) {
            this.ctx.scale(-1, 1);
            x = -x;
        }

        const bubbleWidth = type === 'middle' ? 100 * scaleFactor : 135 * scaleFactor;
        const bubbleHeight = type === 'middle' ? 90 * scaleFactor : 85 * scaleFactor;

        // Skip drawing bubble background if noBubble is true
        if (!bubbleContent.noBubble) {
            this.ctx.drawImage(thoughtImage, x - bubbleWidth / 2, y - bubbleHeight / 2, bubbleWidth, bubbleHeight);
        }

        // Draw content
        if (bubbleContent.action) {
            this.drawWizardBubbleContent(x, y, bubbleContent.action, flip, scaleFactor);
        }

        this.ctx.restore();
    }

    drawWizardBubbleContent(x, y, action, flip, scaleFactor) {
        if (flip) {
            this.ctx.scale(-1, 1);
            x = -x;
        }

        const maximizeImage = (img, maxSize) => {
            const ratio = img.width / img.height;
            let w, h;
            if (ratio > 1) {
                w = maxSize;
                h = maxSize / ratio;
            } else {
                h = maxSize;
                w = maxSize * ratio;
            }
            return { w, h };
        };

        if (action === 'point_left') {
            const img = this.images.get('signpost-left');
            if (img && img.complete) {
                const maxSize = 55 * scaleFactor;
                const { w, h } = maximizeImage(img, maxSize);
                // Center vertically, and use the user's horizontal offset preference
                this.ctx.drawImage(img, x - w / 1.5, y - h / 2, w, h);
            }
        } else if (action === 'point_right') {
            const img = this.images.get('signpost-right');
            if (img && img.complete) {
                const maxSize = 56 * scaleFactor;
                const { w, h } = maximizeImage(img, maxSize);
                this.ctx.drawImage(img, x - w / 3, y - h / 2, w, h); // Using similar offset logic
            }
        } else if (action === 'do_nothing') {
            // Empty bubble for do nothing
        }
    }

    drawTreasureBeliefContent(x, y, bubbleContent, flip, scaleFactor) {
        const treasureImage = this.images.get('treasure-gold');
        if (!treasureImage) return;

        this.ctx.save();
        if (flip) {
            this.ctx.scale(-1, 1);
            x = -x;
        }

        const treasureSize = 30 * scaleFactor;
        this.ctx.fillStyle = '#333';
        this.ctx.font = `${Math.round(30 * scaleFactor)}px Helvetica, sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';

        const arrow = bubbleContent.goldDir === 'left' ? '←' : '→';
        const arrowWidth = this.ctx.measureText(arrow).width;
        const spacing = 4 * scaleFactor;

        if (bubbleContent.goldDir === 'left') {
            // Arrow on left, treasure on right
            const totalWidth = arrowWidth + spacing + treasureSize;
            let currentX = x - totalWidth / 1.5 + 5 * scaleFactor;

            this.ctx.fillText(arrow, currentX + arrowWidth / 2, y - 4);
            currentX += arrowWidth + spacing;
            this.ctx.drawImage(treasureImage, currentX, y - treasureSize / 1.5, treasureSize, treasureSize);
        } else {
            // Treasure on left, arrow on right
            const totalWidth = treasureSize + spacing + arrowWidth;
            let currentX = x - totalWidth / 2 + 5 * scaleFactor;

            this.ctx.drawImage(treasureImage, currentX, y - treasureSize / 1.5, treasureSize, treasureSize);
            currentX += treasureSize + spacing;
            this.ctx.fillText(arrow, currentX + arrowWidth / 2, y - 4);
        }

        this.ctx.restore();
    }

    drawTreasureNoBeliefContent(x, y, flip, scaleFactor) {
        const treasureImage = this.images.get('treasure-gold');
        if (!treasureImage) return;

        this.ctx.save();
        if (flip) {
            this.ctx.scale(-1, 1);
            x = -x;
        }

        const treasureSize = 30 * scaleFactor;

        // Center treasure with question mark
        const questionMarkWidth = 10 * scaleFactor;
        const spacing = 4 * scaleFactor;
        const totalWidth = treasureSize + spacing + questionMarkWidth;
        let currentX = x - totalWidth / 1.5 + 5 * scaleFactor;

        this.ctx.drawImage(treasureImage, currentX, y - treasureSize / 1.5, treasureSize, treasureSize);
        currentX += treasureSize + spacing;

        this.ctx.fillStyle = '#666';
        this.ctx.font = `${Math.round(30 * scaleFactor)}px Helvetica, sans-serif`;
        this.ctx.textAlign = 'left';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('?', currentX, y - 3);

        this.ctx.restore();
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = BeliefGridWorldRenderer;
}