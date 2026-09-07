HyperToolsSV =
{
    ["Default"] = 
    {
        ["@cpcharles"] = 
        {
            ["$AccountWide"] = 
            {
                ["filterOptions"] = 
                {
                    ["hitValueVisible"] = true,
                    ["damageTypeVisible"] = false,
                    ["abilityIdVisible"] = true,
                    ["powerTypeVisible"] = false,
                    ["targetNameVisible"] = true,
                    ["abilityNameVisible"] = true,
                    ["sourceNameVisible"] = true,
                    ["resultVisible"] = true,
                },
                ["version"] = 32,
                ["trackers"] = 
                {
                    ["Pillager"] = 
                    {
                        ["name"] = "Pillager",
                        ["yOffset"] = 1049,
                        ["expiresAt"] = 
                        {
                            ["Edyr Grimrest"] = 9408.2251898000,
                        },
                        ["inverse"] = false,
                        ["fontWeight"] = "soft-shadow-thick",
                        ["children"] = 
                        {
                        },
                        ["timer1"] = true,
                        ["hideIcon"] = false,
                        ["outlineColor"] = 
                        {
                            [4] = 1,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["sizeY"] = "34",
                        ["parent"] = "HT_Trackers",
                        ["vertical"] = false,
                        ["outlineThickness"] = 1,
                        ["icon"] = "/esoui/art/icons/malatar_agonizingbolts.dds",
                        ["fontSize"] = 18,
                        ["decimals"] = 0,
                        ["show"] = true,
                        ["current"] = 0,
                        ["stacksColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["anchorToGroupMember"] = true,
                        ["target"] = "Yourself",
                        ["textAlignment"] = 1,
                        ["max"] = 0,
                        ["timeColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["type"] = "Progress Bar",
                        ["xOffset"] = "1979",
                        ["backgroundColor"] = 
                        {
                            [4] = 0.5843137503,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["timer2"] = false,
                        ["duration"] = 
                        {
                            ["Edyr Grimrest"] = 45,
                        },
                        ["targetNumber"] = 1,
                        ["textColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["conditions"] = 
                        {
                            [2] = 
                            {
                                ["result"] = "Hide Tracker",
                                ["resultArguments"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 1,
                                },
                                ["arg2"] = 0,
                                ["arg1"] = "Remaining Time",
                                ["operator"] = "==",
                            },
                            [1] = 
                            {
                                ["result"] = "Set Background Color",
                                ["resultArguments"] = 
                                {
                                    [4] = 0.5081967115,
                                    [1] = 0.5098039508,
                                    [2] = 0.1450980455,
                                    [3] = 0.1176470593,
                                },
                                ["arg2"] = 0,
                                ["arg1"] = "Remaining Time",
                                ["operator"] = "==",
                            },
                        },
                        ["drawLevel"] = 0,
                        ["cooldownColor"] = 
                        {
                            [4] = 0.5058823824,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["events"] = 
                        {
                            [1] = 
                            {
                                ["type"] = "Get Effect Cooldown",
                                ["arguments"] = 
                                {
                                    ["luaCodeToExecute"] = "if hyperToolsGlobal.result == 2240 then hyperToolsTracker.expiresAt[GetUnitName('player')] = GetGameTimeSeconds() + 45 hyperToolsTracker.duration[GetUnitName('player')] = 45 end",
                                    ["cooldown"] = "45",
                                    ["Ids"] = 
                                    {
                                        [1] = 172056,
                                    },
                                    ["dontUpdateFromThisEvent"] = true,
                                    ["overwriteShorterDuration"] = false,
                                    ["onlyYourCast"] = false,
                                },
                            },
                        },
                        ["barColor"] = 
                        {
                            [4] = 0.5901639462,
                            [1] = 1,
                            [2] = 0.2392156869,
                            [3] = 0.9215686321,
                        },
                        ["stacks"] = 
                        {
                        },
                        ["sizeX"] = "180",
                        ["load"] = 
                        {
                            ["bosses"] = 
                            {
                            },
                            ["role"] = 0,
                            ["class"] = "Any",
                            ["skills"] = 
                            {
                            },
                            ["inCombat"] = false,
                            ["never"] = false,
                            ["itemSets"] = 
                            {
                            },
                            ["always"] = false,
                            ["zones"] = 
                            {
                            },
                        },
                        ["font"] = "MEDIUM_FONT",
                        ["text"] = "Pillager",
                    },
                    ["Major Brittle"] = 
                    {
                        ["name"] = "Major Brittle",
                        ["yOffset"] = "1049",
                        ["expiresAt"] = 
                        {
                            ["Dreadsail Brewmaster"] = 0,
                            ["Dreadsail Overseer"] = 0,
                            ["Reef Guardian"] = 0,
                            ["Dreadsail Serpent-Tongue"] = 0,
                            ["Resonating Glyphic"] = 0,
                            ["Turlassil"] = 0,
                            ["Dreadsail Ranger"] = 0,
                            ["Tideborn Taleria"] = 9396.6640625000,
                            ["Spirit Crab Broodmother"] = 0,
                            ["Iron Atronach"] = 0,
                            ["Dreadsail Sharpshooter"] = 0,
                            ["Sea Behemoth"] = 0,
                            ["Frost Atronach"] = 0,
                            ["Dreadsail Incendiary"] = 0,
                            ["Coral Drift Senche"] = 0,
                            ["Dreadsail Swindler"] = 0,
                            ["Coral Drift Bear"] = 0,
                            ["Dreadsail Swashbuckler"] = 0,
                            ["Flame Hound"] = 0,
                            ["Reef Viper"] = 0,
                            ["Dreadsail Deadeye"] = 0,
                            ["Bow Breaker"] = 0,
                            ["Lylanar"] = 0,
                            ["Dreadsail Stormrider"] = 0,
                            ["Dreadsail Keelcutter"] = 0,
                            ["Ornaug"] = 0,
                            ["Spirit Reef Viper"] = 0,
                            ["Frost Hound"] = 0,
                        },
                        ["inverse"] = false,
                        ["fontWeight"] = "soft-shadow-thick",
                        ["children"] = 
                        {
                        },
                        ["timer1"] = true,
                        ["hideIcon"] = false,
                        ["outlineColor"] = 
                        {
                            [4] = 1,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["sizeY"] = "34",
                        ["parent"] = "HT_Trackers",
                        ["vertical"] = false,
                        ["outlineThickness"] = 1,
                        ["icon"] = "/esoui/art/icons/ability_debuff_major_brittle.dds",
                        ["fontSize"] = 18,
                        ["decimals"] = 0,
                        ["show"] = true,
                        ["current"] = 0,
                        ["stacksColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["anchorToGroupMember"] = true,
                        ["target"] = "Current Target",
                        ["textAlignment"] = 1,
                        ["max"] = 0,
                        ["timeColor"] = 
                        {
                            [4] = 1,
                            [1] = 0.9921568632,
                            [2] = 1,
                            [3] = 0.9843137264,
                        },
                        ["type"] = "Progress Bar",
                        ["xOffset"] = "1789",
                        ["backgroundColor"] = 
                        {
                            [4] = 0.3770491779,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["timer2"] = false,
                        ["duration"] = 
                        {
                            ["Dreadsail Brewmaster"] = -9281.1461843000,
                            ["Dreadsail Overseer"] = -9273.4350714000,
                            ["Reef Guardian"] = -9187.6394591000,
                            ["Dreadsail Serpent-Tongue"] = -9280.2216606000,
                            ["Resonating Glyphic"] = -9398.0608122000,
                            ["Turlassil"] = -8861.3570739000,
                            ["Dreadsail Ranger"] = -8720.5813282000,
                            ["Tideborn Taleria"] = 1.9692442000,
                            ["Spirit Crab Broodmother"] = -9280.2190672000,
                            ["Iron Atronach"] = -8843.1384523000,
                            ["Dreadsail Sharpshooter"] = -9274.1889539000,
                            ["Sea Behemoth"] = -9346.7293204000,
                            ["Frost Atronach"] = -8856.7360737000,
                            ["Dreadsail Incendiary"] = -9186.6666894000,
                            ["Coral Drift Senche"] = -9176.7981787000,
                            ["Dreadsail Swindler"] = -9238.6290842000,
                            ["Coral Drift Bear"] = -9178.1187174000,
                            ["Dreadsail Swashbuckler"] = -9281.1034354000,
                            ["Flame Hound"] = -8806.7275293000,
                            ["Reef Viper"] = -8722.1029448000,
                            ["Dreadsail Deadeye"] = -9258.7710255000,
                            ["Bow Breaker"] = -9056.7412958000,
                            ["Lylanar"] = -8845.0825251000,
                            ["Dreadsail Stormrider"] = -8702.2579747000,
                            ["Dreadsail Keelcutter"] = -9273.6665953000,
                            ["Ornaug"] = -9259.9397562000,
                            ["Spirit Reef Viper"] = -8448.3605115000,
                            ["Frost Hound"] = -8843.1595615000,
                        },
                        ["targetNumber"] = 1,
                        ["textColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["conditions"] = 
                        {
                            [1] = 
                            {
                                ["result"] = "Hide Tracker",
                                ["resultArguments"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 1,
                                },
                                ["arg2"] = 0,
                                ["arg1"] = "Remaining Time",
                                ["operator"] = "<=",
                            },
                        },
                        ["drawLevel"] = 0,
                        ["cooldownColor"] = 
                        {
                            [4] = 0.8000000119,
                            [1] = 1,
                            [2] = 1,
                            [3] = 0.6000000238,
                        },
                        ["events"] = 
                        {
                            [1] = 
                            {
                                ["type"] = "Get Effect Duration",
                                ["arguments"] = 
                                {
                                    ["luaCodeToExecute"] = "",
                                    ["cooldown"] = "45",
                                    ["Ids"] = 
                                    {
                                        [1] = 145977,
                                    },
                                    ["dontUpdateFromThisEvent"] = false,
                                    ["overwriteShorterDuration"] = false,
                                    ["onlyYourCast"] = false,
                                },
                            },
                        },
                        ["barColor"] = 
                        {
                            [4] = 0.5901639462,
                            [1] = 0,
                            [2] = 0.7098039389,
                            [3] = 1,
                        },
                        ["stacks"] = 
                        {
                            ["Dreadsail Brewmaster"] = 0,
                            ["Dreadsail Overseer"] = 0,
                            ["Reef Guardian"] = 0,
                            ["Dreadsail Serpent-Tongue"] = 0,
                            ["Resonating Glyphic"] = 0,
                            ["Turlassil"] = 0,
                            ["Dreadsail Ranger"] = 0,
                            ["Tideborn Taleria"] = 0,
                            ["Spirit Crab Broodmother"] = 0,
                            ["Iron Atronach"] = 0,
                            ["Dreadsail Sharpshooter"] = 0,
                            ["Sea Behemoth"] = 0,
                            ["Frost Atronach"] = 0,
                            ["Dreadsail Incendiary"] = 0,
                            ["Coral Drift Senche"] = 0,
                            ["Dreadsail Swindler"] = 0,
                            ["Coral Drift Bear"] = 0,
                            ["Dreadsail Swashbuckler"] = 0,
                            ["Flame Hound"] = 0,
                            ["Reef Viper"] = 0,
                            ["Dreadsail Deadeye"] = 0,
                            ["Bow Breaker"] = 0,
                            ["Lylanar"] = 0,
                            ["Dreadsail Stormrider"] = 0,
                            ["Dreadsail Keelcutter"] = 0,
                            ["Ornaug"] = 0,
                            ["Spirit Reef Viper"] = 0,
                            ["Frost Hound"] = 0,
                        },
                        ["sizeX"] = "185",
                        ["load"] = 
                        {
                            ["bosses"] = 
                            {
                            },
                            ["role"] = 0,
                            ["class"] = "Any",
                            ["skills"] = 
                            {
                            },
                            ["inCombat"] = false,
                            ["never"] = false,
                            ["itemSets"] = 
                            {
                            },
                            ["always"] = false,
                            ["zones"] = 
                            {
                            },
                        },
                        ["font"] = "MEDIUM_FONT",
                        ["text"] = "Brittle",
                    },
                    ["none"] = 
                    {
                        ["name"] = "none",
                        ["yOffset"] = 0,
                        ["expiresAt"] = 
                        {
                        },
                        ["inverse"] = false,
                        ["fontWeight"] = "thick-outline",
                        ["children"] = 
                        {
                        },
                        ["timer1"] = true,
                        ["hideIcon"] = false,
                        ["outlineColor"] = 
                        {
                            [4] = 1,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["sizeY"] = 0,
                        ["parent"] = "none",
                        ["vertical"] = false,
                        ["outlineThickness"] = 4,
                        ["icon"] = "",
                        ["fontSize"] = 30,
                        ["decimals"] = 1,
                        ["current"] = 0,
                        ["stacksColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["anchorToGroupMember"] = true,
                        ["target"] = "Yourself",
                        ["max"] = 0,
                        ["textAlignment"] = 1,
                        ["drawLevel"] = 0,
                        ["backgroundColor"] = 
                        {
                            [4] = 0.4000000000,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["type"] = "Progress Tracker",
                        ["xOffset"] = 0,
                        ["timer2"] = true,
                        ["targetNumber"] = 1,
                        ["timeColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["duration"] = 
                        {
                        },
                        ["textColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["conditions"] = 
                        {
                            [1] = 
                            {
                                ["result"] = "Hide Tracker",
                                ["resultArguments"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["arg2"] = 0,
                                ["arg1"] = "Remaining Time",
                                ["operator"] = "<",
                            },
                        },
                        ["IDs"] = 
                        {
                        },
                        ["cooldownColor"] = 
                        {
                            [4] = 0.7000000000,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["events"] = 
                        {
                            [1] = 
                            {
                                ["type"] = "Get Effect Duration",
                                ["arguments"] = 
                                {
                                    ["luaCodeToExecute"] = "",
                                    ["cooldown"] = 8,
                                    ["Ids"] = 
                                    {
                                    },
                                    ["dontUpdateFromThisEvent"] = false,
                                    ["overwriteShorterDuration"] = false,
                                    ["onlyYourCast"] = false,
                                },
                            },
                        },
                        ["barColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["stacks"] = 
                        {
                        },
                        ["sizeX"] = 0,
                        ["load"] = 
                        {
                            ["bosses"] = 
                            {
                            },
                            ["role"] = 2,
                            ["class"] = "Dragonknight",
                            ["skills"] = 
                            {
                            },
                            ["inCombat"] = false,
                            ["never"] = false,
                            ["itemSets"] = 
                            {
                            },
                            ["always"] = false,
                            ["zones"] = 
                            {
                            },
                        },
                        ["font"] = "BOLD_FONT",
                        ["text"] = "none",
                    },
                    ["empower and PA group"] = 
                    {
                        ["name"] = "empower and PA group",
                        ["yOffset"] = -55.2856445312,
                        ["expiresAt"] = 
                        {
                        },
                        ["inverse"] = false,
                        ["fontWeight"] = "thick-outline",
                        ["children"] = 
                        {
                            ["shrooms"] = 
                            {
                                ["name"] = "shrooms",
                                ["yOffset"] = 80,
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0235294122,
                                },
                                ["sizeY"] = "30",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "/esoui/art/icons/ability_buff_minor_intellect.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = 47,
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 1,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                    [2] = 
                                    {
                                        ["result"] = "Set Bar Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0.2392156869,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 0,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = "==",
                                    },
                                    [3] = 
                                    {
                                        ["result"] = "Set Border Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.0901960805,
                                        },
                                        ["arg2"] = 19.9000000000,
                                        ["arg1"] = "Distance to target",
                                        ["operator"] = "<",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [2] = 61737,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [1] = 61706,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "30",
                                ["cooldownColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 1,
                                    [3] = 0.0980392173,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Warden",
                                    ["skills"] = 
                                    {
                                        [1] = 85862,
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = false,
                                    ["itemSets"] = 
                                    {
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                            ["minor berserk"] = 
                            {
                                ["name"] = "minor berserk",
                                ["yOffset"] = 80,
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0235294122,
                                },
                                ["sizeY"] = "30",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "/esoui/art/icons/ability_buff_minor_berserk.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = 47,
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 2,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                    [2] = 
                                    {
                                        ["result"] = "Set Bar Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.2156862766,
                                        },
                                        ["arg2"] = 0,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = "==",
                                    },
                                    [3] = 
                                    {
                                        ["result"] = "Set Border Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.0901960805,
                                        },
                                        ["arg2"] = 19.9000000000,
                                        ["arg1"] = "Distance to target",
                                        ["operator"] = "<",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [2] = 61737,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [2] = 61744,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "30",
                                ["cooldownColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 1,
                                    [3] = 0.0980392173,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Any",
                                    ["skills"] = 
                                    {
                                        [1] = 40094,
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = false,
                                    ["itemSets"] = 
                                    {
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                            ["major brut"] = 
                            {
                                ["name"] = "major brut",
                                ["yOffset"] = "40",
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0235294122,
                                },
                                ["sizeY"] = "45",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "esoui/art/icons/ability_dragonknight_015_a.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = "46",
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 4,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                    [3] = 
                                    {
                                        ["result"] = "Set Border Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.0901960805,
                                        },
                                        ["arg2"] = 35.9900000000,
                                        ["arg1"] = "Distance to target",
                                        ["operator"] = "<",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [2] = 61737,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [2] = 61665,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "45",
                                ["cooldownColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 1,
                                    [3] = 0.0980392173,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Dragonknight",
                                    ["skills"] = 
                                    {
                                        [1] = 31874,
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = false,
                                    ["itemSets"] = 
                                    {
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                            ["minor prophecy"] = 
                            {
                                ["name"] = "minor prophecy",
                                ["yOffset"] = "40",
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0235294122,
                                },
                                ["sizeY"] = "30",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "/esoui/art/icons/ability_buff_minor_prophecy.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = "46",
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 4,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                    [2] = 
                                    {
                                        ["result"] = "Show Proc",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 1,
                                            [2] = 0,
                                            [3] = 0.0352941193,
                                        },
                                        ["arg2"] = 0,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = "==",
                                    },
                                    [3] = 
                                    {
                                        ["result"] = "Set Border Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.0901960805,
                                        },
                                        ["arg2"] = 29.9900000000,
                                        ["arg1"] = "Distance to target",
                                        ["operator"] = "<",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [2] = 61737,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [2] = 61691,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "30",
                                ["cooldownColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 1,
                                    [3] = 0.0980392173,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Sorcerer",
                                    ["skills"] = 
                                    {
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = true,
                                    ["itemSets"] = 
                                    {
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                            ["empower"] = 
                            {
                                ["name"] = "empower",
                                ["yOffset"] = "40",
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0235294122,
                                },
                                ["sizeY"] = "35",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "/esoui/art/icons/ability_buff_major_empower.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = "46",
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 1,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                    [2] = 
                                    {
                                        ["result"] = "Set Bar Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 1,
                                            [2] = 0,
                                            [3] = 0.0352941193,
                                        },
                                        ["arg2"] = 0,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = "==",
                                    },
                                    [3] = 
                                    {
                                        ["result"] = "Set Border Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.0901960805,
                                        },
                                        ["arg2"] = 18.9900000000,
                                        ["arg1"] = "Distance to target",
                                        ["operator"] = "<",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [2] = 61737,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [2] = 61737,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "35",
                                ["cooldownColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 1,
                                    [3] = 0.0980392173,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Necromancer",
                                    ["skills"] = 
                                    {
                                        [1] = 118352,
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = false,
                                    ["itemSets"] = 
                                    {
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                            ["major courage"] = 
                            {
                                ["name"] = "major courage",
                                ["yOffset"] = 38.9999389648,
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["sizeY"] = "30",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "/esoui/art/icons/ability_buff_major_courage.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = 86,
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [2] = 
                                    {
                                        ["result"] = "Show Proc",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 0,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = "==",
                                    },
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 3,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [2] = 61737,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [1] = 109966,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "30",
                                ["cooldownColor"] = 
                                {
                                    [4] = 0.7000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Any",
                                    ["skills"] = 
                                    {
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = true,
                                    ["itemSets"] = 
                                    {
                                        [1] = "|H1:item:138530:364:50:54484:370:50:2:0:0:0:0:0:0:0:2049:73:0:1:0:179:0|h|h",
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                            ["PA(2)"] = 
                            {
                                ["name"] = "PA(2)",
                                ["yOffset"] = 41,
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 1,
                                    [3] = 0.1411764771,
                                },
                                ["sizeY"] = "45",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "/esoui/art/icons/ability_healer_019.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = "-5",
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [4] = 
                                    {
                                        ["result"] = "Set Bar Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.5725490451,
                                        },
                                        ["arg2"] = 0,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = "==",
                                    },
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 3,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                    [2] = 
                                    {
                                        ["result"] = "Show Proc",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 0,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = "==",
                                    },
                                    [3] = 
                                    {
                                        ["result"] = "Set Border Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 1,
                                            [2] = 0,
                                            [3] = 0.0823529437,
                                        },
                                        ["arg2"] = 11.9000000000,
                                        ["arg1"] = "Distance to target",
                                        ["operator"] = ">",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [1] = 61771,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [1] = 61771,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "45",
                                ["cooldownColor"] = 
                                {
                                    [4] = 0.7000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Any",
                                    ["skills"] = 
                                    {
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = false,
                                    ["itemSets"] = 
                                    {
                                        [1] = "|H1:item:117098:364:50:26845:370:50:4:0:0:0:0:0:0:0:2049:25:0:1:0:130:0|h|h",
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                            ["major resolve"] = 
                            {
                                ["name"] = "major resolve",
                                ["yOffset"] = "40",
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0235294122,
                                },
                                ["sizeY"] = "45",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "/esoui/art/icons/ability_buff_major_resolve.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = "46",
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 4,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                    [3] = 
                                    {
                                        ["result"] = "Set Border Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.0901960805,
                                        },
                                        ["arg2"] = 35.9900000000,
                                        ["arg1"] = "Distance to target",
                                        ["operator"] = "<",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [2] = 61737,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [1] = 61694,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "45",
                                ["cooldownColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 1,
                                    [3] = 0.0980392173,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Warden",
                                    ["skills"] = 
                                    {
                                        [1] = 86126,
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = true,
                                    ["itemSets"] = 
                                    {
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                            ["minor sorc"] = 
                            {
                                ["name"] = "minor sorc",
                                ["yOffset"] = "40",
                                ["expiresAt"] = 
                                {
                                },
                                ["inverse"] = false,
                                ["fontWeight"] = "thick-outline",
                                ["children"] = 
                                {
                                },
                                ["timer1"] = false,
                                ["hideIcon"] = false,
                                ["outlineColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0235294122,
                                },
                                ["sizeY"] = "30",
                                ["parent"] = "empower and PA group",
                                ["vertical"] = false,
                                ["outlineThickness"] = 2,
                                ["icon"] = "/esoui/art/icons/ability_buff_minor_sorcery.dds",
                                ["fontSize"] = 20,
                                ["decimals"] = 1,
                                ["show"] = true,
                                ["current"] = 0,
                                ["stacksColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["anchorToGroupMember"] = true,
                                ["target"] = "Group",
                                ["textAlignment"] = 1,
                                ["max"] = 0,
                                ["timer2"] = false,
                                ["type"] = "Icon Tracker",
                                ["xOffset"] = "46",
                                ["backgroundColor"] = 
                                {
                                    [4] = 0.4000000000,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 0,
                                },
                                ["duration"] = 
                                {
                                },
                                ["timeColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 0,
                                    [3] = 0.0274509806,
                                },
                                ["targetNumber"] = 1,
                                ["textColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["conditions"] = 
                                {
                                    [1] = 
                                    {
                                        ["result"] = "Hide Tracker",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 0,
                                            [3] = 1,
                                        },
                                        ["arg2"] = 4,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = ">",
                                    },
                                    [2] = 
                                    {
                                        ["result"] = "Show Proc",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 1,
                                            [2] = 0,
                                            [3] = 0.0352941193,
                                        },
                                        ["arg2"] = 0,
                                        ["arg1"] = "Remaining Time",
                                        ["operator"] = "==",
                                    },
                                    [3] = 
                                    {
                                        ["result"] = "Set Border Color",
                                        ["resultArguments"] = 
                                        {
                                            [4] = 1,
                                            [1] = 0,
                                            [2] = 1,
                                            [3] = 0.0901960805,
                                        },
                                        ["arg2"] = 29.9900000000,
                                        ["arg1"] = "Distance to target",
                                        ["operator"] = "<",
                                    },
                                },
                                ["IDs"] = 
                                {
                                    [2] = 61737,
                                },
                                ["drawLevel"] = 0,
                                ["events"] = 
                                {
                                    [1] = 
                                    {
                                        ["arguments"] = 
                                        {
                                            ["luaCodeToExecute"] = "",
                                            ["cooldown"] = 0,
                                            ["Ids"] = 
                                            {
                                                [1] = 61685,
                                            },
                                            ["dontUpdateFromThisEvent"] = false,
                                            ["overwriteShorterDuration"] = false,
                                            ["onlyYourCast"] = false,
                                        },
                                        ["argument1"] = 0,
                                        ["type"] = "Get Effect Duration",
                                    },
                                },
                                ["barColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 1,
                                    [2] = 1,
                                    [3] = 1,
                                },
                                ["stacks"] = 
                                {
                                },
                                ["sizeX"] = "30",
                                ["cooldownColor"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 1,
                                    [3] = 0.0980392173,
                                },
                                ["load"] = 
                                {
                                    ["bosses"] = 
                                    {
                                    },
                                    ["role"] = 0,
                                    ["class"] = "Templar",
                                    ["skills"] = 
                                    {
                                    },
                                    ["inCombat"] = false,
                                    ["never"] = true,
                                    ["itemSets"] = 
                                    {
                                    },
                                    ["always"] = false,
                                    ["zones"] = 
                                    {
                                    },
                                },
                                ["font"] = "BOLD_FONT",
                            },
                        },
                        ["timer1"] = true,
                        ["hideIcon"] = false,
                        ["outlineColor"] = 
                        {
                            [4] = 0,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["sizeY"] = "100",
                        ["parent"] = "HT_Trackers",
                        ["vertical"] = false,
                        ["outlineThickness"] = 2,
                        ["icon"] = "esoui/art/icons/gear_bloodforge_light_head_a.dds",
                        ["fontSize"] = 16,
                        ["decimals"] = 1,
                        ["show"] = true,
                        ["current"] = 0,
                        ["stacksColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["anchorToGroupMember"] = true,
                        ["target"] = "Yourself",
                        ["textAlignment"] = 1,
                        ["max"] = 0,
                        ["timer2"] = true,
                        ["type"] = "Group Member",
                        ["xOffset"] = 21,
                        ["backgroundColor"] = 
                        {
                            [4] = 0,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["duration"] = 
                        {
                        },
                        ["timeColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["targetNumber"] = 1,
                        ["textColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["conditions"] = 
                        {
                            [2] = 
                            {
                                ["result"] = "Hide Tracker",
                                ["resultArguments"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 1,
                                },
                                ["arg2"] = 4,
                                ["arg1"] = "Group Role",
                                ["operator"] = "==",
                            },
                            [1] = 
                            {
                                ["result"] = "Hide Tracker",
                                ["resultArguments"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 1,
                                },
                                ["arg2"] = 2,
                                ["arg1"] = "Group Role",
                                ["operator"] = "==",
                            },
                        },
                        ["IDs"] = 
                        {
                        },
                        ["drawLevel"] = 0,
                        ["events"] = 
                        {
                            [1] = 
                            {
                                ["arguments"] = 
                                {
                                    ["luaCodeToExecute"] = "  ",
                                    ["dontUpdateFromThisEvent"] = false,
                                    ["Ids"] = 
                                    {
                                    },
                                    ["overwriteShorterDuration"] = false,
                                    ["onlyYourCast"] = false,
                                },
                                ["argument1"] = 0,
                                ["type"] = "Get Effect Duration",
                            },
                        },
                        ["barColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["stacks"] = 
                        {
                        },
                        ["sizeX"] = "100",
                        ["cooldownColor"] = 
                        {
                            [4] = 0.7000000000,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["load"] = 
                        {
                            ["bosses"] = 
                            {
                            },
                            ["role"] = 0,
                            ["class"] = "Any",
                            ["skills"] = 
                            {
                            },
                            ["inCombat"] = false,
                            ["never"] = true,
                            ["itemSets"] = 
                            {
                            },
                            ["always"] = false,
                            ["zones"] = 
                            {
                            },
                        },
                        ["font"] = "BOLD_FONT",
                    },
                    ["Major Vuln"] = 
                    {
                        ["name"] = "Major Vuln",
                        ["yOffset"] = "1011",
                        ["expiresAt"] = 
                        {
                            ["Dreadsail Brewmaster"] = 0,
                            ["Target Iron Atronach, Trial"] = 8618.5126953125,
                            ["Reef Guardian"] = 0,
                            ["Dreadsail Serpent-Tongue"] = 0,
                            ["Tideborn Taleria"] = 0,
                            ["Turlassil"] = 0,
                            ["Dreadsail Keelcutter"] = 0,
                            ["Resonating Glyphic"] = 9243.3945312500,
                            ["Target Deadlands Harvester, Trial"] = 8618.5126953125,
                            ["Iron Atronach"] = 0,
                            ["Dreadsail Sharpshooter"] = 0,
                            ["Dreadsail Overseer"] = 0,
                            ["Frost Atronach"] = 0,
                            ["Coral Drift Haj Mota"] = 0,
                            ["Coral Drift Senche"] = 0,
                            ["Dreadsail Swindler"] = 0,
                            ["Bow Breaker"] = 0,
                            ["Dreadsail Swashbuckler"] = 0,
                            ["Ornaug"] = 0,
                            ["Reef Viper"] = 0,
                            ["Dreadsail Deadeye"] = 0,
                            ["Dreadsail Stormrider"] = 0,
                            ["Lylanar"] = 0,
                            ["Dreugh"] = 0,
                            ["Coral Drift Bear"] = 0,
                            ["Dreadsail Ranger"] = 0,
                            ["Spirit Reef Viper"] = 0,
                            ["Spirit Crab Broodmother"] = 0,
                        },
                        ["inverse"] = false,
                        ["fontWeight"] = "soft-shadow-thick",
                        ["children"] = 
                        {
                        },
                        ["timer1"] = true,
                        ["hideIcon"] = false,
                        ["outlineColor"] = 
                        {
                            [4] = 1,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["sizeY"] = "34",
                        ["parent"] = "HT_Trackers",
                        ["vertical"] = false,
                        ["outlineThickness"] = 1,
                        ["icon"] = "/esoui/art/icons/ability_necromancer_006_a.dds",
                        ["fontSize"] = 18,
                        ["decimals"] = 0,
                        ["show"] = true,
                        ["current"] = 0,
                        ["stacksColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["anchorToGroupMember"] = true,
                        ["target"] = "Boss",
                        ["textAlignment"] = 1,
                        ["max"] = 0,
                        ["timeColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 0.9803921580,
                            [3] = 0.9843137264,
                        },
                        ["type"] = "Progress Bar",
                        ["xOffset"] = "1789",
                        ["backgroundColor"] = 
                        {
                            [4] = 0.5000000000,
                            [1] = 0.0313725509,
                            [2] = 0.0196078438,
                            [3] = 0.1098039225,
                        },
                        ["timer2"] = false,
                        ["duration"] = 
                        {
                            ["Dreadsail Brewmaster"] = -9281.1469301000,
                            ["Target Iron Atronach, Trial"] = -0.5962168875,
                            ["Reef Guardian"] = -9187.6395911000,
                            ["Dreadsail Serpent-Tongue"] = -9280.2220739000,
                            ["Tideborn Taleria"] = -9394.6911752000,
                            ["Turlassil"] = -8861.3562975000,
                            ["Dreadsail Keelcutter"] = -9273.6660589000,
                            ["Resonating Glyphic"] = 16.9939846500,
                            ["Target Deadlands Harvester, Trial"] = -0.5968182875,
                            ["Iron Atronach"] = -8836.3768920000,
                            ["Dreadsail Sharpshooter"] = -9274.1874523000,
                            ["Dreadsail Overseer"] = -9273.4358349000,
                            ["Frost Atronach"] = -8793.0446200000,
                            ["Coral Drift Haj Mota"] = -9038.5545261000,
                            ["Coral Drift Senche"] = -9176.7983350000,
                            ["Dreadsail Swindler"] = -8698.7670764000,
                            ["Bow Breaker"] = -9056.7428421000,
                            ["Dreadsail Swashbuckler"] = -9281.1038780000,
                            ["Ornaug"] = -8949.1791256000,
                            ["Reef Viper"] = -8722.1025875000,
                            ["Dreadsail Deadeye"] = -9227.3703939000,
                            ["Dreadsail Stormrider"] = -8698.7231277000,
                            ["Lylanar"] = -8831.5489142000,
                            ["Dreugh"] = -8947.8527836000,
                            ["Coral Drift Bear"] = -9178.1190279000,
                            ["Dreadsail Ranger"] = -8720.5808117000,
                            ["Spirit Reef Viper"] = -9236.0673847000,
                            ["Spirit Crab Broodmother"] = -9280.2185176000,
                        },
                        ["targetNumber"] = 1,
                        ["textColor"] = 
                        {
                            [4] = 1,
                            [1] = 1,
                            [2] = 1,
                            [3] = 1,
                        },
                        ["conditions"] = 
                        {
                            [2] = 
                            {
                                ["result"] = "Set Background Color",
                                ["resultArguments"] = 
                                {
                                    [4] = 0.5882353187,
                                    [1] = 0.0313725509,
                                    [2] = 0.0235294122,
                                    [3] = 0.1176470593,
                                },
                                ["arg2"] = 0,
                                ["arg1"] = "Remaining Time",
                                ["operator"] = "==",
                            },
                            [1] = 
                            {
                                ["result"] = "Hide Tracker",
                                ["resultArguments"] = 
                                {
                                    [4] = 1,
                                    [1] = 0,
                                    [2] = 0,
                                    [3] = 1,
                                },
                                ["arg2"] = 0,
                                ["arg1"] = "Remaining Time",
                                ["operator"] = "==",
                            },
                        },
                        ["drawLevel"] = 0,
                        ["cooldownColor"] = 
                        {
                            [4] = 0.5058823824,
                            [1] = 0,
                            [2] = 0,
                            [3] = 0,
                        },
                        ["events"] = 
                        {
                            [1] = 
                            {
                                ["type"] = "Get Effect Duration",
                                ["arguments"] = 
                                {
                                    ["luaCodeToExecute"] = "",
                                    ["cooldown"] = 0,
                                    ["Ids"] = 
                                    {
                                        [1] = 106754,
                                    },
                                    ["dontUpdateFromThisEvent"] = false,
                                    ["overwriteShorterDuration"] = false,
                                    ["onlyYourCast"] = false,
                                },
                            },
                        },
                        ["barColor"] = 
                        {
                            [4] = 0.5882353187,
                            [1] = 0.4235294163,
                            [2] = 0.2941176593,
                            [3] = 1,
                        },
                        ["stacks"] = 
                        {
                            ["Dreadsail Brewmaster"] = 0,
                            ["Target Iron Atronach, Trial"] = 0,
                            ["Reef Guardian"] = 0,
                            ["Dreadsail Serpent-Tongue"] = 0,
                            ["Tideborn Taleria"] = 0,
                            ["Turlassil"] = 0,
                            ["Dreadsail Keelcutter"] = 0,
                            ["Resonating Glyphic"] = 0,
                            ["Target Deadlands Harvester, Trial"] = 0,
                            ["Iron Atronach"] = 0,
                            ["Dreadsail Sharpshooter"] = 0,
                            ["Dreadsail Overseer"] = 0,
                            ["Frost Atronach"] = 0,
                            ["Coral Drift Haj Mota"] = 0,
                            ["Coral Drift Senche"] = 0,
                            ["Dreadsail Swindler"] = 0,
                            ["Bow Breaker"] = 0,
                            ["Dreadsail Swashbuckler"] = 0,
                            ["Ornaug"] = 0,
                            ["Reef Viper"] = 0,
                            ["Dreadsail Deadeye"] = 0,
                            ["Dreadsail Stormrider"] = 0,
                            ["Lylanar"] = 0,
                            ["Dreugh"] = 0,
                            ["Coral Drift Bear"] = 0,
                            ["Dreadsail Ranger"] = 0,
                            ["Spirit Reef Viper"] = 0,
                            ["Spirit Crab Broodmother"] = 0,
                        },
                        ["sizeX"] = "185",
                        ["load"] = 
                        {
                            ["bosses"] = 
                            {
                            },
                            ["role"] = 0,
                            ["class"] = "Any",
                            ["skills"] = 
                            {
                            },
                            ["inCombat"] = false,
                            ["never"] = false,
                            ["itemSets"] = 
                            {
                            },
                            ["always"] = false,
                            ["zones"] = 
                            {
                            },
                        },
                        ["font"] = "MEDIUM_FONT",
                        ["text"] = "Vulnerability",
                    },
                },
            },
        },
    },
}
