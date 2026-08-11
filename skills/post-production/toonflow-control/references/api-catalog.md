# ToonFlow API Catalog (140+ endpoints)

All endpoints use **POST** method. Base URL: `http://127.0.0.1:{port}`

## Login (whitelisted — no auth needed)
- `POST /api/login/login` — Login with `{username, password}`, returns JWT token

## Project Management
- `POST /api/project/addProject` — Create project
- `POST /api/project/getProject` — List all projects
- `POST /api/project/delProject` — Delete project
- `POST /api/project/editProject` — Edit project
- `POST /api/project/addDirectorManual` — Add director manual
- `POST /api/project/queryDirectorManual` — Query director manual
- `POST /api/project/addVisualManual` — Add visual manual
- `POST /api/project/getVisualManual` — Get visual manual
- `POST /api/project/getModelDetails` — Get model details for project

## Novel & Script
- `POST /api/novel/addNovel` — Import novel
- `POST /api/novel/getNovel` — List novels
- `POST /api/novel/delNovel` — Delete novel
- `POST /api/novel/updateNovel` — Update novel
- `POST /api/novel/getNovelData` — Get novel data
- `POST /api/novel/getNovelEventState` — Get event extraction state
- `POST /api/novel/event/generateEvents` — Extract chapter events
- `POST /api/novel/event/getEvent` — Get events
- `POST /api/script/addScript` — Add script
- `POST /api/script/getScrptApi` — Get scripts
- `POST /api/script/delScript` — Delete script
- `POST /api/script/updateScript` — Update script
- `POST /api/script/extractAssets` — Extract assets from script
- `POST /api/script/exportScript` — Export script

## Script Agent
- `POST /api/scriptAgent/getPlanData` — Get plan data
- `POST /api/scriptAgent/setPlanData` — Set plan data
- `POST /api/scriptAgent/updateData` — Update agent data
- `POST /api/agents/getMemory` — Get agent memory
- `POST /api/agents/clearMemory` — Clear agent memory

## Art Styles
- `POST /api/artStyle/getArtStyle` — List art styles
- `POST /api/artStyle/addArtStyle` — Add art style
- `POST /api/artStyle/editArtStyle` — Edit art style
- `POST /api/artStyle/extractStylePrompt` — Extract style prompt

## Assets
- `POST /api/assets/addAssets` — Add assets
- `POST /api/assets/getAssetsApi` — Get assets
- `POST /api/assets/saveAssets` — Save assets
- `POST /api/assets/delAssets` — Delete assets
- `POST /api/assets/updateAssets` — Update assets
- `POST /api/assets/batchDelete` — Batch delete
- `POST /api/assets/uploadClip` — Upload clip
- `POST /api/assetsGenerate/generateAssets` — Generate assets
- `POST /api/assetsGenerate/batchGenerateImageAssets` — Batch generate images
- `POST /api/assetsGenerate/polishAssetsPrompt` — Polish asset prompts

## Production — Storyboard
- `POST /api/production/storyboard/getStoryboardData` — Get storyboard data
- `POST /api/production/storyboard/addStoryboard` — Add storyboard entry
- `POST /api/production/storyboard/editStoryboardInfo` — Edit storyboard
- `POST /api/production/storyboard/batchAddStoryboardInfo` — Batch add
- `POST /api/production/storyboard/batchDelete` — Batch delete
- `POST /api/production/storyboard/batchGenerateImage` — Batch generate storyboard images
- `POST /api/production/storyboard/pollingImage` — Poll image generation
- `POST /api/production/storyboard/removeFrame` — Remove frame

## Production — Workbench (Video)
- `POST /api/production/workbench/addTrack` — Add video track
- `POST /api/production/workbench/deleteTrack` — Delete track
- `POST /api/production/workbench/generateVideo` — Generate single video
- `POST /api/production/workbench/batchGenerateVideo` — Batch generate videos
- `POST /api/production/workbench/generateVideoPrompt` — Generate video prompt
- `POST /api/production/workbench/batchGeneratePrompt` — Batch generate prompts
- `POST /api/production/workbench/getVideoList` — Get video list
- `POST /api/production/workbench/checkVideoStateList` — Check video status
- `POST /api/production/workbench/delVideo` — Delete video
- `POST /api/production/workbench/selectVideo` — Select video
- `POST /api/production/workbench/updateVideoDuration` — Update duration
- `POST /api/production/workbench/getGenerateData` — Get generation data

## Production — Image Editing
- `POST /api/production/editImage/generateFlowImage` — Generate image from flow
- `POST /api/production/editImage/getImageFlow` — Get image flow
- `POST /api/production/editImage/saveImageFlow` — Save image flow
- `POST /api/production/editImage/uploadImage` — Upload image
- `POST /api/production/getFlowData` — Get flow data
- `POST /api/production/saveFlowData` — Save flow data

## Settings — Vendor Config
- `POST /api/setting/vendorConfig/getVendorList` — List all vendors
- `POST /api/setting/vendorConfig/addVendor` — Add vendor
- `POST /api/setting/vendorConfig/deleteVendor` — Delete vendor
- `POST /api/setting/vendorConfig/enableVendor` — Toggle vendor
- `POST /api/setting/vendorConfig/updateVendorInputs` — Set API keys
- `POST /api/setting/vendorConfig/addVendorModel` — Add model
- `POST /api/setting/vendorConfig/delVendorModel` — Delete model
- `POST /api/setting/vendorConfig/upVendorModel` — Update model
- `POST /api/setting/vendorConfig/modelTest` — Test model connection
- `POST /api/setting/vendorConfig/getCodeByLink` — Get vendor code

## Settings — Agent Deploy
- `POST /api/setting/agentDeploy/getAgentDeploy` — List agents (17 total)
- `POST /api/setting/agentDeploy/deployAgentModel` — Assign model to agent
- `POST /api/setting/agentDeploy/agentSetKey` — Set agent key
- `POST /api/setting/agentDeploy/updateAgentModel` — Update agent model
- `POST /api/setting/agentDeploy/getAgentUseMode` — Get usage mode
- `POST /api/setting/agentDeploy/updateUseMode` — Update usage mode

## Settings — Skills
- `POST /api/setting/skillManagement/getSkillList` — List skill files
- `POST /api/setting/skillManagement/getSkillContent` — Read skill content
- `POST /api/setting/skillManagement/saveSkillContent` — Save skill content

## Settings — Other
- `POST /api/setting/loginConfig/getUser` — Get current user
- `POST /api/setting/loginConfig/updateUserPwd` — Change password
- `POST /api/setting/dbConfig/dbInfo` — DB info
- `POST /api/setting/dbConfig/exportData` — Export data
- `POST /api/setting/dbConfig/importData` — Import data
- `POST /api/setting/dbConfig/clearData` — Clear all data
- `POST /api/setting/memoryConfig/getMemory` — Get memory config
- `POST /api/setting/memoryConfig/delAllMemory` — Delete all memory
- `POST /api/setting/modelMap/getPromptList` — Get prompt templates
- `POST /api/setting/modelMap/savePrompt` — Save prompt template
- `POST /api/other/getVersion` — Get app version
