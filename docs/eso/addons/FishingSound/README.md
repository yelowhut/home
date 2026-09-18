FishingSound is a lightweight ESO addon that gives you an instant audio cue when a fish bites — even when the official fishing events fail to fire.
It uses ESO’s internal controller vibration event to detect bites with 100% reliability, making it the most accurate bite‑alert method available.

Whether you’re casually fishing or grinding Master Angler, FishingSound helps you react faster and never miss a bite again.

How It Works 

Using "EVENT_VIBRATION" 

When a Fish bites, there is a EVENT called "EVENT_VIBRATION", which will allways have the same parameters as follows
[1] = 2500 
[2] = 0.0099999997764826...
[3] = 0.05000000.. 
[4] = 0 
[5] = 0
[6] = ""

[1] = Is the Duration of the Vibration
[2-3] = Are the Vibration Intensitys

The Addon checks if the EVENT = "EVENT_VIBRATION" was fired and if it matches 2500ms. 
Most Vibrations are only about 500ms, I did not encounter any overlapings so for, but could be buggy if it did. 

Shout out to the cool Addon "Zgoo High Isle" Author "Rhyono", which helped me to detect EVENTS in ESO and parameters to test this. 


Customization

In the settings ADDONS -> Fishing Sound , are the different Sounds, which you can select and if you want to disable the addon you can do that too. 

The Souds were handpicked by the Addon "Sound Board" by "Miguel"
which suited best for recognition. 

@FloIstImGame is my ESO User and feel free to Mail me in Game


Screen Vignette (local addition)

Besides the sound, a coloured glow can blink along the edges of the screen while a fish is on the hook.

It is drawn as four plain quads, one per screen edge, with no texture art at all: each quad gets its
corner colours set via SetVertexColors, the two outer corners at full alpha and the two inner ones at
alpha 0, so the engine interpolates the gradient. That is what makes the colour picker work for any
colour instead of only shades of the baked-in red of the game's own overlay textures.

The blinking starts on the same EVENT_VIBRATION bite that triggers the sound and keeps going until you
are no longer fishing: GetInteractionType() is polled every 100 ms and anything other than
INTERACTION_FISH (reeled in, interrupted, walked away, died) stops it. A configurable safety timeout
stops it as well, in case a bite is never resolved. The overlay lives in a top level window attached to
HUD_SCENE / HUD_UI_SCENE, so it disappears in menus, inventory and loading screens, and it has the mouse
disabled so it never eats a click.

Settings, in ADDONS -> Fishing Sound:

- Enable Vignette
- Colour
- Opacity - how opaque the glow is right at the screen edge
- Thickness - depth of the gradient, in percent of the screen
- Blink Style - pulse (smooth), strobe (hard on/off), solid (fade in and hold)
- Blink Speed - length of one blink cycle in milliseconds
- Safety Timeout - hard stop in seconds
- Active Edges - top / bottom / left / right
- Test Vignette - runs it for four seconds

Slash commands: /fishingvignette toggles it, /fishingvignettetest previews it.
