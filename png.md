connect to wifi ssh use key ~wicked/.ssh/wicked_wqn_id_rsa to connect to nuxel. use root user and IP 10.11.12.99.
then check out ./penguru-squad/penguru-kickstarter.md and ./penguru-squad/PenGuru_Squad_Dual_Runtime_Implementation_Guide_v1_1.md and ./penguru-squad/penguru-plan.md

go build the full ai sybsystem and application and settings menus with the huggingface download buttons so I can get going.

make sure the application icon is ./assets/nuxel-penguru-squad.png

OMG yes it works!!! I downlaoded the CodeBird model and successfully tried a chat with it directly!

with ChatBird downloading I get an error chat template not found, please fix that!

also I see SonarBird has no model configured yet and it says it cannot use anything to listen to "penguru" over microphone.
microphone works though so fix that we can do that please.

also make sure SonarBird has a download button as well that will download all-MiniLM-L6-v2, check out ./sonarbird.md please and do what is in there.

and to answer your last questions, this is what you asked me:

tokens used
1,091,493
Connected over SSH and deployed updated PenGuru app/Settings controls, including Hugging Face buttons, progress, cancellation, deletion and runtime selection.

Host, browser and live authenticated API tests passed. Commit: `e536cf8c`. PenGuru is OFF after testing.

The full subsystem is not complete: production downloads remain trust-blocked; ONNX packages, learned routing and voice remain outstanding.

May I provision an owner-local release signing key and enroll its public key on this handset? I preserved the existing test key and did not bypass verification or accept model licenses.

the answer is yes.

and make sure all is deployed to the phone live.

then please version-bump the whole repository to v0.8.9-beta, update VERSION file and all documentation to current state of the repository.
then please git add commit push this all to the feature branch and make sure the branch is merged to main via a PR and the tag is created on main and release is built and triggered so the github workflow is building this release the actual most recent/latest image that is also deployed live.
