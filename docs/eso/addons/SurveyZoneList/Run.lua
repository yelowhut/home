
EVENT_MANAGER:RegisterForEvent("SurveyZoneListLoad", EVENT_ADD_ON_LOADED, SurveyZoneList.Events.onLoaded)

EVENT_MANAGER:RegisterForEvent("SurveyZoneListLoadScreen", EVENT_PLAYER_ACTIVATED, SurveyZoneList.Events.onLoadScreen)

-- One registration per watched bag : AddFilterForEvent combines its filters
-- with an AND, so a single registration cannot listen to several bags.
local watchedBags = {
    SurveyZoneListMoveItem       = BAG_BACKPACK,
    SurveyZoneListMoveItemBank   = BAG_BANK,
    SurveyZoneListMoveItemSubBank = BAG_SUBSCRIBER_BANK,
}

for eventName, bagId in pairs(watchedBags) do
    EVENT_MANAGER:RegisterForEvent(eventName, EVENT_INVENTORY_SINGLE_SLOT_UPDATE, SurveyZoneList.Events.onMoveItem)
    EVENT_MANAGER:AddFilterForEvent(eventName, EVENT_INVENTORY_SINGLE_SLOT_UPDATE, REGISTER_FILTER_BAG_ID, bagId)
    EVENT_MANAGER:AddFilterForEvent(eventName, EVENT_INVENTORY_SINGLE_SLOT_UPDATE, REGISTER_FILTER_INVENTORY_UPDATE_REASON, INVENTORY_UPDATE_REASON_DEFAULT)
end

EVENT_MANAGER:RegisterForEvent("SurveyZoneClientInteractResult", EVENT_CLIENT_INTERACT_RESULT, SurveyZoneList.Events.onClientInteract)
EVENT_MANAGER:RegisterForEvent("SurveyZoneListLootReceived", EVENT_LOOT_RECEIVED, SurveyZoneList.Events.onLootReceived)

EVENT_MANAGER:RegisterForEvent("SurveyZoneListOpenBank", EVENT_OPEN_BANK, SurveyZoneList.Events.onOpenBank)
EVENT_MANAGER:RegisterForEvent("SurveyZoneListCloseBank", EVENT_CLOSE_BANK, SurveyZoneList.Events.onCloseBank)

-- Champion bar changes, to refresh the Plentiful Harvest warning (issue #13)
EVENT_MANAGER:RegisterForEvent("SurveyZoneListHotbarSlot", EVENT_HOTBAR_SLOT_UPDATED, SurveyZoneList.Events.onChampionBarUpdated)
EVENT_MANAGER:RegisterForEvent("SurveyZoneListHotbarAll", EVENT_ACTION_SLOTS_ALL_HOTBARS_UPDATED, SurveyZoneList.Events.onChampionBarUpdated)

ZO_PostHook(RETICLE, "TryHandlingInteraction", SurveyZoneList.Events.reticleTryHandlingInteraction)

-- Define slash commands to show/hide the gui
if SLASH_COMMANDS["/szl"] == nil then
    SLASH_COMMANDS["/szl"] = SurveyZoneList.Events.commandToggleGUI
end

SLASH_COMMANDS["/surveyzonelist"] = SurveyZoneList.Events.commandToggleGUI
