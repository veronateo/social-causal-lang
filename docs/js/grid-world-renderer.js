/**
 * Grid World Renderer
 */

class GridWorldRenderer {
    constructor(canvas, config = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // Handle high DPI displays for crisp rendering
        const pixelRatio = window.devicePixelRatio || 1;

        // Default configuration for single lane
        this.config = {
            laneLength: 19,    // Number of positions in the lane
            maxWidth: 1200,    // Maximum canvas width
            laneHeight: 80,   // Height of the lane
            laneColor: '#ddd',
            animationSpeed: 600,
            horizontalBorder: 20,  // Border space on left and right
            verticalBorder: 20,    // Extra border space above and below
            pixelRatio: pixelRatio,
            imageBasePath: 'images',  // Base path for images (can be overridden)
            ...config
        };

        // Calculate cell size to fit within max width (accounting for borders)
        this.config.cellSize = Math.floor((this.config.maxWidth - 2 * this.config.horizontalBorder) / this.config.laneLength);

        // Calculate scale factor based on maxWidth (1200 is the original default)
        this.config.scaleFactor = this.config.maxWidth / 1200;

        // Set canvas display size 
        const minRequiredWidth = this.config.laneLength * this.config.cellSize + 2 * this.config.horizontalBorder;
        const position18X = this.config.horizontalBorder + 18 * this.config.cellSize;
        const requiredWidthForPosition18 = position18X + this.config.cellSize + this.config.horizontalBorder; // position 18 + cell width + right border
        const displayWidth = Math.max(minRequiredWidth, requiredWidthForPosition18);
        const displayHeight = this.config.laneHeight + Math.round(160 * this.config.scaleFactor) + 2 * this.config.verticalBorder;

        this.canvas.style.width = displayWidth + 'px';
        this.canvas.style.height = displayHeight + 'px';

        // Set canvas buffer size for high DPI
        this.canvas.width = displayWidth * pixelRatio;
        this.canvas.height = displayHeight * pixelRatio;

        // Scale the context to match the device pixel ratio
        this.ctx.scale(pixelRatio, pixelRatio);

        // Configure image smoothing for crisp rendering
        this.ctx.imageSmoothingEnabled = true;
        this.ctx.imageSmoothingQuality = 'high';

        // Store display dimensions for calculations
        this.displayWidth = displayWidth;
        this.displayHeight = displayHeight;

        // Animation state
        this.animationFrame = null;
        this.isAnimating = false;
        this.currentScene = null;
        this.frameIndex = 0;

        // Image storage
        this.images = new Map();

        // Load images
        this.loadImages();
    }


    loadImages() {
        // Load actual image files
        const basePath = this.config.imageBasePath;
        const imageFiles = {
            farmer: `${basePath}/farmer.png`,
            wizard: `${basePath}/wizard.png`,
            'wizard-wand': `${basePath}/wizard-wand.png`,
            lightning: `${basePath}/lightning.png`,
            apple: `${basePath}/apple.png`,
            banana: `${basePath}/banana.png`,
            rock: `${basePath}/rock.png`,
            thought: `${basePath}/thought.png`
        };

        Object.entries(imageFiles).forEach(([name, src]) => {
            this.loadImage(name, src);
        });
    }

    loadImage(name, src) {
        const img = new Image();
        img.onload = () => {
            this.images.set(name, img);
        };
        img.onerror = () => {
            console.warn(`Failed to load image: ${src}`);
        };
        img.src = src;
    }

    drawLane() {
        const { laneLength, cellSize, laneHeight, laneColor, horizontalBorder, verticalBorder } = this.config;

        // Clear entire canvas
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

        // Calculate exact lane width
        const exactLaneWidth = laneLength * cellSize;

        // Center the lane horizontally in the canvas
        const laneX = Math.round((this.displayWidth - exactLaneWidth) / 2);
        const laneY = verticalBorder + 10;

        // Draw lane background
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(laneX, laneY, exactLaneWidth, laneHeight - 20);

        // Draw lane borders
        this.ctx.strokeStyle = laneColor;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(laneX, laneY, exactLaneWidth, laneHeight - 20);

        this.ctx.strokeStyle = laneColor;
        this.ctx.lineWidth = 1;
        for (let i = 1; i < laneLength; i++) {
            const dividerX = laneX + i * cellSize;
            this.ctx.beginPath();
            this.ctx.moveTo(dividerX, laneY);
            this.ctx.lineTo(dividerX, laneY + laneHeight - 20);
            this.ctx.stroke();
        }

        // Store lane position for other methods
        this.laneX = laneX;
    }

    drawEntity(entity, highlighted = false) {
        const { cellSize, laneHeight, laneLength, horizontalBorder, verticalBorder } = this.config;

        // Use the stored lane position from drawLane
        const x = this.laneX + entity.position * cellSize;
        const y = verticalBorder + 15; // Fixed vertical position in lane

        if (entity.type === 'wizard') return;

        const image = this.images.get(entity.type);

        if (image && image.complete && image.naturalHeight !== 0) {
            // Calculate image size and position
            const imgSize = Math.min(cellSize - 10, laneHeight - 30);
            const imgX = Math.round(x + (cellSize - imgSize) / 2);
            const imgY = Math.round(y + (laneHeight - 30 - imgSize) / 2);

            // White background
            this.ctx.fillStyle = '#ffffff';
            this.ctx.fillRect(imgX, imgY, imgSize, imgSize);

            // Save context and apply additional smoothing for this image
            this.ctx.save();
            this.ctx.imageSmoothingEnabled = true;
            this.ctx.imageSmoothingQuality = 'high';

            // Draw image on top with rounded coordinates for crisp rendering
            this.ctx.drawImage(image, imgX, imgY, imgSize, imgSize);

            this.ctx.restore();
        }
    }

    getEntityColor(type) {
        const colors = {
            farmer: '#4CAF50',
            wizard: '#9C27B0',
            apple: '#F44336',
            banana: '#FFEB3B',
            rock: '#757575'
        };
        return colors[type] || '#333';
    }

    renderFrame(scene, frameIndex = 0) {
        this.drawLane();

        if (!scene || !scene.frames || frameIndex >= scene.frames.length) {
            return;
        }

        const frame = scene.frames[frameIndex];

        // Store current frame index for text rendering
        this.currentFrameIndex = frameIndex;

        // Always highlight the rock position to show where magical effects occur
        this.drawCellHighlight(14);

        // Draw entities in specific order: goals first, then rocks, then farmer last (so farmer appears on top)
        const goals = frame.entities.filter(e => e.type === 'apple' || e.type === 'banana');
        const rocks = frame.entities.filter(e => e.type === 'rock');
        const farmers = frame.entities.filter(e => e.type === 'farmer');
        const others = frame.entities.filter(e => !['apple', 'banana', 'rock', 'farmer', 'wizard'].includes(e.type));

        [...goals, ...rocks, ...others, ...farmers].forEach(entity => {
            this.drawEntity(entity, entity.highlighted);
        });

        // Draw action indicator if present
        if (frame.action) {
            this.drawActionIndicator(frame.action);
        }

        // Draw wizard below lane
        const wizard = frame.entities.find(e => e.type === 'wizard');
        if (wizard) {
            this.drawWizard(wizard);
        }

        // Draw thought bubbles if present
        if (frame.thoughtBubbles) {
            this.drawThoughtBubbles(frame.thoughtBubbles);
        }

        // Draw descriptive text
        this.drawDescriptiveText(frame, this.currentFrameIndex);
    }

    drawWizard(wizard) {
        const { cellSize, laneHeight, laneLength, horizontalBorder, verticalBorder, scaleFactor } = this.config;

        // Determine which wizard image to use based on the wizard's state
        const imageKey = wizard.withWand ? 'wizard-wand' : 'wizard';
        const image = this.images.get(imageKey);

        if (image) {
            const wizardSize = Math.round(60 * scaleFactor);
            const x = Math.round(this.laneX + wizard.position * cellSize + (cellSize - wizardSize) / 2);
            const y = Math.round(verticalBorder + laneHeight + 60 * scaleFactor);

            // Save context and apply smoothing for crisp wizard rendering
            this.ctx.save();
            this.ctx.imageSmoothingEnabled = true;
            this.ctx.imageSmoothingQuality = 'high';

            this.ctx.drawImage(image, x, y, wizardSize, wizardSize);

            this.ctx.restore();
        }
    }

    drawActionIndicator(action) {
        const { cellSize, laneHeight, laneLength, horizontalBorder, verticalBorder } = this.config;

        if (action.type === 'wave_wand') {
            // Draw magical wand effect at the target position (where rock will appear)
            const x = this.laneX + action.position * cellSize + cellSize / 2;
            const y = verticalBorder + laneHeight / 2;
        }

        if (action.type === 'place_rock' || action.type === 'add_rock') {
            // Draw appearance effect
            const x = this.laneX + action.position * cellSize + cellSize / 2;
            const y = verticalBorder + laneHeight / 2;
        }

        if (action.type === 'remove_rock') {
            // Draw disappearance effect
            const x = this.laneX + action.position * cellSize + cellSize / 2;
            const y = verticalBorder + laneHeight / 2;
        }

        if (action.type === 'lightning_effect') {
            // Draw lightning effect at the target position
            this.drawLightningEffect(action.position);
        }
    }

    drawCellHighlight(position) {
        const { cellSize, laneHeight, laneLength, horizontalBorder, verticalBorder } = this.config;

        const x = this.laneX + position * cellSize;
        const y = verticalBorder + 10;

        // Draw thick black border around the cell
        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = 4;
        this.ctx.strokeRect(x + 2, y, cellSize - 4, laneHeight - 20);
    }

    drawLightningEffect(position) {
        const { cellSize, laneHeight, laneLength, horizontalBorder, verticalBorder, scaleFactor } = this.config;

        const lightningImage = this.images.get('lightning');

        if (lightningImage) {
            const lightningSize = 40 * scaleFactor;
            const x = Math.round(this.laneX + position * cellSize + (cellSize - lightningSize) / 2);
            const y = Math.round(verticalBorder + laneHeight + 5 * scaleFactor); // Position below the lane

            this.ctx.save();
            this.ctx.imageSmoothingEnabled = true;
            this.ctx.imageSmoothingQuality = 'high';

            // Draw lightning effect below the lane
            this.ctx.drawImage(lightningImage, x, y, lightningSize, lightningSize);

            this.ctx.restore();
        }
    }

    async playAnimation(scene, options = {}) {
        // Always stop any current animation first
        if (this.isAnimating) {
            this.stopAnimation();
        }

        this.currentScene = scene;
        this.isAnimating = true;
        this.frameIndex = 0;

        const {
            loop = false,
            onFrameChange = null,
            onComplete = null,
            speed = this.config.animationSpeed
        } = options;

        // Show the first frame immediately
        this.renderFrame(scene, this.frameIndex);
        if (onFrameChange) {
            onFrameChange(this.frameIndex, scene.frames[this.frameIndex]);
        }

        const animate = () => {
            if (!this.isAnimating) return;

            this.frameIndex++;

            if (this.frameIndex >= scene.frames.length) {
                if (loop) {
                    this.frameIndex = 0;
                } else {
                    this.isAnimating = false;
                    if (onComplete) onComplete();
                    return;
                }
            }

            this.renderFrame(scene, this.frameIndex);

            if (onFrameChange) {
                onFrameChange(this.frameIndex, scene.frames[this.frameIndex]);
            }

            setTimeout(() => {
                if (this.isAnimating) {
                    this.animationFrame = requestAnimationFrame(animate);
                }
            }, speed);
        };

        // Start the animation after the initial delay
        setTimeout(() => {
            if (this.isAnimating) {
                this.animationFrame = requestAnimationFrame(animate);
            }
        }, speed);
    }

    stopAnimation() {
        this.isAnimating = false;
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
        // Reset frame index to ensure consistent state
        this.frameIndex = 0;
        this.currentScene = null;
    }

    drawThoughtBubbles(thoughtBubbles) {
        const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
        const wizardX = this.laneX + 9 * cellSize + cellSize / 2; // Center of wizard position
        const wizardY = verticalBorder + laneHeight + 15 * scaleFactor;

        // Draw left thought bubble if present (flipped)
        if (thoughtBubbles.left) {
            this.drawSingleThoughtBubble(wizardX - 60 * scaleFactor, wizardY + 20 * scaleFactor, thoughtBubbles.left, true);
        }

        // Draw right thought bubble if present (normal)
        if (thoughtBubbles.right) {
            this.drawSingleThoughtBubble(wizardX + 60 * scaleFactor, wizardY + 20 * scaleFactor, thoughtBubbles.right, false);
        }
    }

    drawSingleThoughtBubble(x, y, bubbleContent, flip = false) {
        const thoughtImage = this.images.get('thought');
        const { scaleFactor } = this.config;

        if (!thoughtImage || !thoughtImage.complete) {
            return; // Skip if image not loaded
        }

        // Ensure bubbleContent always has a state property
        if (!bubbleContent || !bubbleContent.state) {
            console.warn('Thought bubble missing state, defaulting to empty:', bubbleContent);
            bubbleContent = { state: 'empty', position: 14 };
        }

        this.ctx.save();

        // Apply horizontal flip if needed
        if (flip) {
            this.ctx.scale(-1, 1);
            x = -x; // Flip the x coordinate
        }

        // Draw the thought bubble image
        const bubbleWidth = 70 * scaleFactor;
        const bubbleHeight = 50 * scaleFactor;
        this.ctx.drawImage(thoughtImage, x - bubbleWidth / 2, y - bubbleHeight / 2, bubbleWidth, bubbleHeight);

        // Draw content inside bubble (overlay on the thought bubble)
        // Match the actual grid cell dimensions (taller than wide)
        const contentWidth = 16 * scaleFactor;
        const contentHeight = 22 * scaleFactor; // Taller to match the grid cells
        const contentX = x - contentWidth / 2 + 5 * scaleFactor;
        const contentY = y - contentHeight / 2; // Slightly above center

        if (bubbleContent.state === 'rock') {
            // Draw mini rock using the rock image
            const rockImage = this.images.get('rock');
            if (rockImage && rockImage.complete) {
                // Rock should not be flipped and should be smaller than the grid cell
                const rockWidth = 20 * scaleFactor;  // Keep rock smaller
                const rockHeight = 20 * scaleFactor;
                const rockX = x - rockWidth / 2 + 5 * scaleFactor;
                const rockY = y - rockHeight / 2;

                if (flip) {
                    // If this is a flipped bubble, counter-flip the rock to keep it normal
                    this.ctx.save();
                    this.ctx.scale(-1, 1);
                    this.ctx.drawImage(rockImage, -rockX - rockWidth, rockY, rockWidth, rockHeight);
                    this.ctx.restore();
                } else {
                    this.ctx.drawImage(rockImage, rockX, rockY, rockWidth, rockHeight);
                }
            }
        } else if (bubbleContent.state === 'rock-with-cross') {
            // Draw rock with red cross on top
            const rockImage = this.images.get('rock');
            if (rockImage && rockImage.complete) {
                const rockWidth = 20 * scaleFactor;
                const rockHeight = 20 * scaleFactor;
                const rockX = x - rockWidth / 2 + 5 * scaleFactor;
                const rockY = y - rockHeight / 2;

                // Draw rock first
                if (flip) {
                    this.ctx.save();
                    this.ctx.scale(-1, 1);
                    this.ctx.drawImage(rockImage, -rockX - rockWidth, rockY, rockWidth, rockHeight);
                    this.ctx.restore();
                } else {
                    this.ctx.drawImage(rockImage, rockX, rockY, rockWidth, rockHeight);
                }

                // Draw red cross on top
                this.ctx.strokeStyle = '#ff0000';
                this.ctx.lineWidth = 3 * scaleFactor;
                this.ctx.lineCap = 'round';

                const crossSize = 12 * scaleFactor;
                const crossCenterX = x + 5 * scaleFactor;
                const crossCenterY = y;

                // Draw X
                this.ctx.beginPath();
                this.ctx.moveTo(crossCenterX - crossSize / 2, crossCenterY - crossSize / 2);
                this.ctx.lineTo(crossCenterX + crossSize / 2, crossCenterY + crossSize / 2);
                this.ctx.moveTo(crossCenterX + crossSize / 2, crossCenterY - crossSize / 2);
                this.ctx.lineTo(crossCenterX - crossSize / 2, crossCenterY + crossSize / 2);
                this.ctx.stroke();
            }
        } else if (bubbleContent.state === 'empty') {
            // For truly empty bubbles (do nothing), don't draw anything inside
            // Just leave the thought bubble empty
        } else {
            // Fallback for any other states - draw empty grid cell
            this.ctx.strokeStyle = '#000000';
            this.ctx.lineWidth = 2 * scaleFactor;
            this.ctx.strokeRect(contentX, contentY, contentWidth, contentHeight);

            // Add inner space to make it look like an empty cell
            this.ctx.fillStyle = '#ffffff';
            this.ctx.fillRect(contentX + 1, contentY + 1, contentWidth - 2, contentHeight - 2);
        }

        this.ctx.restore();
    }

    drawDescriptiveText(frame, frameIndex) {
        // Determine what text to show based on frame content
        const text = this.getDescriptiveText(frame, frameIndex);

        if (!text) return;

        // Position text below the wizard
        const textY = this.config.verticalBorder + this.config.laneHeight + 140 * this.config.scaleFactor;
        const textX = this.displayWidth / 2;

        // Clear the text area
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(0, textY - 10, this.displayWidth, 40);

        // Draw the text
        this.ctx.fillStyle = '#666666';
        const fontSize = Math.round(14 + 2 * this.config.scaleFactor);
        this.ctx.font = `italic ${fontSize}px Arial, sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(text, textX, textY + 10);
    }

    getDescriptiveText(frame, frameIndex) {
        // Determine if this is early in the sequence (wizard observing)
        const isEarlyFrame = frameIndex <= 2;

        // Check if wizard has decided (has only one thought bubble)
        const thoughtBubbles = frame.thoughtBubbles;
        const hasDecided = thoughtBubbles &&
            ((thoughtBubbles.left && !thoughtBubbles.right) ||
                (!thoughtBubbles.left && thoughtBubbles.right));

        // Check if wizard is taking action
        const wizard = frame.entities.find(e => e.type === 'wizard');
        const isActing = wizard && wizard.withWand;

        if (isEarlyFrame && !hasDecided) {
            return "The wizard looks at what's happening.";
        } else if (hasDecided || isActing) {
            // Determine what action the wizard decided on
            const actionText = this.getWizardActionText(thoughtBubbles, frame);
            return `The wizard decides to ${actionText}.`;
        }

        return null;
    }

    getWizardActionText(thoughtBubbles, frame) {
        if (!thoughtBubbles) return "do nothing";

        // Check which bubble is shown (the decided action)
        if (thoughtBubbles.left && !thoughtBubbles.right) {
            // Left bubble (do nothing) is shown
            return "do nothing";
        } else if (thoughtBubbles.right && !thoughtBubbles.left) {
            // Right bubble (take action) is shown
            const rightBubble = thoughtBubbles.right;
            if (rightBubble.state === 'rock') {
                return "add a rock";
            } else if (rightBubble.state === 'rock-with-cross') {
                return "remove the rock";
            }
        }

        return "do nothing";
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GridWorldRenderer;
} 