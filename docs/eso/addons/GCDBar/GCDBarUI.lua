GCDBar = GCDBar or { }
local gb = GCDBar

gb.UI = { }

local WM = GetWindowManager()

local function _setPos()
	local x, y = gb.savedVars.frameX, gb.savedVars.frameY
	gb.UI.gbFrame:ClearAnchors()
	gb.UI.gbFrame:SetAnchor(TOPLEFT, GuiRoot, TOPLEFT, x, y)
end

local function _savePos()
	gb.savedVars.frameX = gb.UI.gbFrame:GetLeft()
	gb.savedVars.frameY = gb.UI.gbFrame:GetTop()
	gb.savedVars.width = gb.UI.gbFrame:GetWidth()
	gb.savedVars.height = gb.UI.gbFrame:GetHeight()
end

function gb.UI.setProperties()
	local r, g, b, a = unpack(gb.savedVars.color)
	gb.UI.gbFront:SetCenterColor(r, g, b, a)
	gb.UI.gbFront:SetEdgeColor(r, g, b, 0.0001)
	gb.UI.gbFront:ClearAnchors()
	if gb.savedVars.reverse then
		gb.UI.gbFront:SetAnchor(RIGHT, gb.UI.gbFrame, RIGHT, 0, 0)
	else
		gb.UI.gbFront:SetAnchor(LEFT, gb.UI.gbFrame, LEFT, 0, 0)
	end
	-- Size / scale
	gb.UI.gbFrame:SetScale(gb.savedVars.scale or 1)
	gb.UI.gbFrame:SetDimensions(gb.savedVars.width, gb.savedVars.height)
	-- Background color
	if gb.UI.gbBack then
		local br, bg, bb, ba = unpack(gb.savedVars.backColor)
		gb.UI.gbBack:SetCenterColor(br, bg, bb, ba)
		gb.UI.gbBack:SetEdgeColor(br, bg, bb, ba)
	end
end

-- Set the bar opacity instantly (children, so the HUD scene fragment on the frame is not disturbed).
function gb.UI.setChildAlpha(alpha)
	if gb.UI.gbBack then gb.UI.gbBack:SetAlpha(alpha) end
	if gb.UI.gbFront then gb.UI.gbFront:SetAlpha(alpha) end
end

-- Smoothly fade the bar opacity to a target (used on combat-state transitions).
function gb.UI.fadeTo(target)
	if not gb.UI.gbFront then return end
	if gb.UI.fadeAnim then gb.UI.fadeAnim:Stop() gb.UI.fadeAnim = nil end
	local startA = gb.UI.gbFront:GetAlpha()
	if math.abs(startA - target) < 0.001 then
		gb.UI.setChildAlpha(target)
		return
	end
	local timeline = ANIMATION_MANAGER:CreateTimeline()
	for _, ctrl in ipairs({ gb.UI.gbBack, gb.UI.gbFront }) do
		if ctrl then
			local anim = timeline:InsertAnimation(ANIMATION_ALPHA, ctrl, 0)
			anim:SetAlphaValues(startA, target)
			anim:SetDuration(300)
			anim:SetEasingFunction(ZO_EaseOutQuadratic)
		end
	end
	timeline:PlayFromStart()
	gb.UI.fadeAnim = timeline
end

function gb.UI.setHudToggle(value)
	if value then
		SCENE_MANAGER:GetScene("hud"):AddFragment(gb.UI.gbFrag)
		SCENE_MANAGER:GetScene("hudui"):AddFragment(gb.UI.gbFrag)
	else
		SCENE_MANAGER:GetScene("hud"):RemoveFragment(gb.UI.gbFrag)
		SCENE_MANAGER:GetScene("hudui"):RemoveFragment(gb.UI.gbFrag)
	end
end

function gb.UI.buildUI()
	local gbFrame = WM:CreateTopLevelWindow("GCDBarFrame")
	gbFrame:SetClampedToScreen(true)
	gbFrame:SetDimensions(gb.savedVars.width, gb.savedVars.height)
	gbFrame:ClearAnchors()
	gbFrame:SetMouseEnabled(false)
	gbFrame:SetMovable(false)
	gbFrame:SetHidden(false)
	gbFrame:SetResizeHandleSize(5)
	gbFrame:SetDimensionConstraints(50, 20, 500, 100)
	gbFrame:SetHandler("OnMoveStop", function(...) _savePos() end)
	gbFrame:SetHandler("OnResizeStop", function(...) _savePos() end)
	
	local gbBack = WM:CreateControl("GCDBarBackdrop", gbFrame, CT_BACKDROP)
	gbBack:SetAnchorFill()
	gbBack:SetCenterColor(0, 0, 0, .25)
	gbBack:SetEdgeColor(0, 0, 0, .25)
	gbBack:SetEdgeTexture(nil, 1, 1, 0, 0)
	gbBack:SetHidden(false)

	local gbFront = WM:CreateControl("GCDBarFront", gbFrame, CT_BACKDROP)
	gbFront:SetAnchor(LEFT, gbFrame, LEFT, 0, 0)
	gbFront:SetCenterColor(1, 0, 0, .7)
	gbFront:SetEdgeColor(1, 0, 0, .01)
	gbFront:SetEdgeTexture(nil, 1, 1, 0, 0)
	gbFront:SetHidden(false)

	gb.UI.gbFrame = gbFrame
	gb.UI.gbBack = gbBack
	gb.UI.gbFront = gbFront
	gb.UI.gbFrag = ZO_HUDFadeSceneFragment:New(gb.UI.gbFrame)
	gb.UI.setHudToggle(true)
	_setPos()
end

