// Auto-generated from FastAPI OpenAPI schema by scripts/gen_api_types.py (EPK-04).
// Run: ./master/venv/Scripts/python.exe scripts/gen_api_types.py

export const API_CONTRACT_VERSION = "0.1.0";
export const API_ROUTE_COUNT = 326;

/** @typedef {AccountingResponse} AccountingResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {AdminResponse} AdminResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {AgentResponse} AgentResponse_Contract
 * @property {*} [agents]
 */
/** @typedef {ApiEnvelope} ApiEnvelope_Contract
 */
/** @typedef {AssistantResponse} AssistantResponse_Contract
 * @property {*} [content]
 */
/** @typedef {AuthResponse} AuthResponse_Contract
 * @property {*} [authenticated]
 * @property {*} [user]
 */
/** @typedef {ChatResponse} ChatResponse_Contract
 * @property {string} [content]
 * @property {string} [task_type]
 * @property {string} [used_model]
 */
/** @typedef {CodeRunResponse} CodeRunResponse_Contract
 * @property {number} [exit_code]
 * @property {string} [stderr]
 * @property {string} [stdout]
 * @property {boolean} [timed_out]
 */
/** @typedef {DistributedResponse} DistributedResponse_Contract
 * @property {*} [status]
 */
/** @typedef {DomainResponse} DomainResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {EvalStudioResponse} EvalStudioResponse_Contract
 * @property {*} [kappa]
 * @property {*} [ok]
 */
/** @typedef {GatewayResponse} GatewayResponse_Contract
 * @property {*} [status]
 */
/** @typedef {HaResponse} HaResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {HallucinationResponse} HallucinationResponse_Contract
 * @property {*} [passed]
 */
/** @typedef {HealthResponse} HealthResponse_Contract
 * @property {string} [status]
 */
/** @typedef {IdeResponse} IdeResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {MemoryResponse} MemoryResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {MlOpsResponse} MlOpsResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {NotebookResponse} NotebookResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {OrchestratorResponse} OrchestratorResponse_Contract
 * @property {*} [intent]
 */
/** @typedef {OrgResponse} OrgResponse_Contract
 * @property {*} [ok]
 * @property {*} [orgs]
 */
/** @typedef {PrivacyResponse} PrivacyResponse_Contract
 * @property {*} [ok]
 * @property {*} [proof_id]
 */
/** @typedef {ProjectResponse} ProjectResponse_Contract
 * @property {*} [projects]
 */
/** @typedef {RagResponse} RagResponse_Contract
 * @property {*} [results]
 */
/** @typedef {ReadyResponse} ReadyResponse_Contract
 * @property {Object} [components]
 * @property {string} [status]
 */
/** @typedef {StudioResponse} StudioResponse_Contract
 * @property {*} [ok]
 */
/** @typedef {UserProfileResponse} UserProfileResponse_Contract
 * @property {*} [user_id]
 */
/** @typedef {UxResponse} UxResponse_Contract
 * @property {*} [ok]
 */
export const API_SCHEMA_NAMES = ["AcceptInviteRequest", "AccountingResponse", "AdminResponse", "AgentProfile", "AgentResponse", "AnnotateRequest", "AnonymizeReq", "ApiEnvelope", "ApprovalBody", "ApprovalDecisionBody", "ArchivePageRequest", "ArchiveSearchRequest", "AsrWerRequest", "AssistantResponse", "AudioConvertBody", "AuthResponse", "BenchmarkScores", "Body_api_handwriting_ocr_api_rag_ocr_handwriting_post", "Body_api_ingest_file_api_rag_ingest_file_post", "Body_chat_api_assistant_chat_post", "Body_chat_stream_api_assistant_chat_stream_post", "Body_create_balloon_job_api_cnc_balloon_post", "Body_create_project_api_projects_post", "Body_restore_enterprise_backup_api_admin_backup_restore_post", "Body_transcribe_voice_clip_api_assistant_transcribe_post", "BuildExeRequest", "BuildReq", "CanaryCheckReq", "ChatResponse", "CircuitRequest", "CodeRunRequest", "CodeRunResponse", "CodeTranslateBody", "ConflictDetectRequest", "ConflictResolveRequest", "ConnectorScanBody", "ConsolidateRequest", "CreateCollectionReq", "CreateInviteRequest", "CreateNotebookRequest", "CreateOrgRequest", "CreateProfileBody", "CreateUserRequest", "CronValidateRequest", "CustomAgentBody", "CustomAgentRequest", "DapSessionRequest", "DecryptRequest", "DiagramReq", "DispatchNotificationRequest", "DistributedResponse", "DomainKbQueryRequest", "DomainResponse", "DriftReq", "DrugInteractionRequest", "EncryptRequest", "EvalStartRequest", "EvalStudioResponse", "EvaluateMeasurementsRequest", "ExamGradeRequest", "FactBody", "FeedbackRequest", "FileResult", "FixTaskRequest", "FlagBody", "FlashcardCreateRequest", "FlashcardReviewRequest", "ForecastReq", "GCodeReq", "GameBuildReq", "GatewayResponse", "GcodeAuditRequest", "GenerateRequest", "GeocodeBody", "GradeSubmissionRequest", "HTTPValidationError", "HaResponse", "HallucinationResponse", "HardwareSpec", "HealthReq", "HealthResponse", "HeartbeatRequest", "HunkDiffReq", "IcsEventBody", "IdeResponse", "IdempotentCommitRequest", "ImportIpynbRequest", "IngestTextReq", "InstallPackageRequest", "IpAllowlistBody", "IterateRequest", "KappaRequest", "LanguageDrillRequest", "LeakageCheckRequest", "LeaseRequest", "LessonPlanRequest", "LevelCheckReq", "LoginRequest", "LspDiagnosticsRequest", "MCPCallReq", "MCPCreateReq", "MCPUpdateReq", "MailMergeBody", "MasteryUpdateRequest", "McpRpcRequest", "MemoryResponse", "MergeReq", "MlOpsResponse", "MultiDiffRequest", "NotebookResponse", "NumericVerifyRequest", "NutritionRequest", "OpenAIChatRequest", "OpenAIEmbeddingsRequest", "OrchestratorResponse", "OrgResponse", "OtelSpanRequest", "ParentChildRequest", "PasswordCheckBody", "PlanReq", "PrivacyResponse", "ProfileReq", "ProjectInstructionBody", "ProjectResponse", "PromoteModelRequest", "PublishPackageRequest", "QuantityTakeoffRequest", "QuizRequest", "QuotaUpdateRequest", "RagResponse", "RbacCheckRequest", "ReadyResponse", "RecordUsageRequest", "RegexTestBody", "RegisterAdapterReq", "RegisterChannelRequest", "RegisterRequest", "RemediateReq", "RepairRequest", "RerankRequest", "ResearchReq", "ResetPasswordRequest", "RobotsCheckRequest", "RollbackAgentRequest", "RollbackModelRequest", "RunCellRequest", "RunRequest", "SaveFileRequest", "SavedChatBody", "ScanPayloadRequest", "Scene3dRequest", "ScheduleJobBody", "SearchReq", "SecretScanBody", "SelectAgentReq", "SetupRequest", "ShareReq", "SignWebhookRequest", "SlideQaRequest", "SourceDownloadBody", "SqlAnalyticsRequest", "SrtRequest", "StatTestReq", "StudioResponse", "SurveyBody", "TableRowsBody", "TailscaleDiagReq", "TargetedEditRequest", "TaskResultRequest", "TaxRequest", "TextBody", "TotpCodeRequest", "TotpVerifyBody", "TranslateQueryBody", "TripPlanRequest", "UnitConvertReq", "UpdateBalloonsRequest", "UpdateProfileBody", "UserProfileResponse", "UxResponse", "ValidationError", "VerifyPayload", "VerifyReleaseRequest", "VerifyWebhookRequest", "VideoAnalyzeRequest", "VideoGenerateBody", "VqaRequest", "WorkspaceActionRequest", "WorkspaceExecRequest", "WorkspaceGitRequest", "WrongReportReq"];
