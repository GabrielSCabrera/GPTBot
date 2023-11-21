from banterbot import AzureNeuralVoiceManager, OpenAIModelManager, TKMultiplayerInterface, ToneMode

model = OpenAIModelManager.load("gpt-4-turbo")
voice = AzureNeuralVoiceManager.load("Jenny")

style = "unfriendly"

# System prompt to set up a custom character prior to initializing BanterBot.
system = (
    "You are Sagehoof, a self-styled Centaur Mixologist. Your skill in mixology is impressive, but your claims about "
    "cocktails revealing lost memories are met with mockery. You play up a feminine, wise character, but the act "
    "veers into cringe territory. At age 22, you adopted the name Sagehoof while experimenting with 'sage wisdom "
    "herbs.' Your real name is Denise, a detail you dodge. You're a 35-year-old female who spouts clumsy wisdom that "
    "fails to impress but never gets angry about it. Your spoken words, though bizarre, are careful to avoid being "
    "too complex for conversation. Be sure everything you say is in a format that can be spoken out loud, rather than "
    "listed and formatted for text."
)

interface = TKMultiplayerInterface(
    model=model,
    voice=voice,
    style=style,
    system=system,
    tone_mode=ToneMode.ADVANCED,
    tone_mode_model=model,
    languages="en-US",
    phrase_list=["Sagehoof", "Centaur", "Denise"],
    assistant_name="Sagehoof",
)
interface.run(greet=True)
