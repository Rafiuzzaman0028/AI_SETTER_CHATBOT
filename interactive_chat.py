# JamieBot/interactive_chat.py
from app.orchestrator import Orchestrator
from app.state_machine.states import ConversationState

def run_chat():
    orchestrator = Orchestrator()
    
    current_state = ConversationState.ENTRY
    extracted_attributes = {}
    
    print("\n==============================")
    print(" Jamie AI Setter — CLI Tester ")
    print("==============================")
    print("Type 'exit' to quit.\n")
    
    while True:
        user_message = input("You: ").strip()
        
        if user_message.lower() == "exit":
            print("\nExiting chat.\n")
            break
        
        result = orchestrator.process_message(
            user_message=user_message,
            current_state=current_state,
            extracted_attributes=extracted_attributes,
        )
        
        print("\nJamie:")
        print(result["reply"])
        print(f"\n[STATE → {result['next_state']}]\n")
        
        # Update state and memory
        current_state = ConversationState(result["next_state"])
        extracted_attributes = result.get(
            "extracted_attributes", extracted_attributes
        )
        
        # End conversation cleanly
        if current_state == ConversationState.END:
            print("Conversation ended.\n")
            break

if __name__ == "__main__":
    run_chat()
