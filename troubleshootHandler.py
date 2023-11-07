import json
import os
from langchain.schema import SystemMessage
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
import keys
import databaseHandler
import sys
sys.path.append('./APIcalls')
import APIcalls.directchatHistory as directchatHistory
import openai
from anytree import Node, RenderTree
from langchain.evaluation import load_evaluator, EmbeddingDistance
from gpt4all import GPT4All

class TroubleshootHandler:

    root = Node("Can you please provide more information about the issue you are facing?", answers={})

    rootnode = Node("Is it sunny?", answers={'yes': None, 'no': None})
    hot_node = Node("Is it hot?", parent=rootnode, answers={'yes': None, 'no': None})
    cold_node = Node("Is it cold?", parent=rootnode, answers={'yes': None, 'no': None})

    rootnode.answers["yes"] = hot_node
    rootnode.answers["no"] = cold_node

    def __init__(self, openAI_APIKEY):
        self.openAI_APIKEY = openAI_APIKEY
        os.environ['OPENAI_API_KEY'] = openAI_APIKEY
        with open('whitelist.json', 'r') as file:
            self.whitelist = json.load(file)

    def isSameQuestionGPT(self, question1, question2):
        prompt = "I will provide you a question 1 and question 2. Figure out if it is the same question, just posed differently."

        system_msg = "You will be deciding whether 2 questions you will be given are the same. Output should ONLY be yes/no"

        prompt += "\n\nQuestion1: " + question1
        prompt += "\nQuestion2: " + question2 + "\n\n"

        response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=[{"role": "system", "content": system_msg},
                                                {"role": "user", "content": prompt}])
        answer = response["choices"][0]["message"]["content"]
        answer = answer.lower()
        print("-------------------------------")
        print("question1: ", question1)
        print("question2: ", question2)
        print("score: ", answer)
        print("-------------------------------")
        if "yes" in answer:
            return True
        return False
    
    def isSameAnswerGPT(self, answer1, answer2):
        prompt = "I will provide you a answer 1 and answer 2. Figure out if it is the same answer, just posed differently."

        system_msg = "You will be deciding whether 2 answers you will be given are the same. Output should ONLY be yes/no"

        prompt += "\n\nQuestion1: " + answer1
        prompt += "\nQuestion2: " + answer2 + "\n\n"

        response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=[{"role": "system", "content": system_msg},
                                                {"role": "user", "content": prompt}])
        answer = response["choices"][0]["message"]["content"]
        answer = answer.lower()
        print("-------------------------------")
        print("question1: ", answer1)
        print("answer2: ", answer2)
        print("score: ", answer)
        print("-------------------------------")
        if "yes" in answer:
            return True
        return False

    def isSameQuestion(self, question1, question2):
        evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
        distance = evaluator.evaluate_string_pairs(
            prediction=question1, prediction_b=question2
        )
        
        print("-------------------------------")
        print("question1: ", question1)
        print("question2: ", question2)
        print("score: ", distance)
        print("-------------------------------")
        if distance["score"] < 0.4:
            return True
        return False

    def isSameAnswer(self, answer1, answer2):
        evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
        distance = evaluator.evaluate_string_pairs(
            prediction=answer1, prediction_b=answer2
        )
        
        print("-------------------------------")
        print("answer1: ", answer1)
        print("answer2: ", answer2)
        print("score: ", distance)
        print("-------------------------------")
        
        if distance["score"] < 0.4:
            return True
        return False

    def getSuggestedQuestion(self, currentNode, user_input):
        print(currentNode)
        print("-------------------------------------------------")
        print("cc: ", currentNode.answers)
        for answerOption in currentNode.answers:
            #print("ao: ", answerOption)
            print(currentNode.answers[answerOption])
            print(self.getSuggestedQuestion(currentNode.answers[answerOption], user_input))
                    
        
    def addToTree(self, QnA, parentNode, currentNode, previousAnswer, skipQuestionCompare=False):
        if len(QnA) <= 0:
            #print("parent node: ", parentNode)
            return parentNode

        question = QnA[0]["question"]
        answer = QnA[0]["answer"]
        #QnA = QnA[1:]

        if self.isSameQuestionGPT(question, currentNode.name):
            if skipQuestionCompare:
                print("same question skip compare")
            QnA = QnA[1:]
            print("same question")
            for answerOption in currentNode.answers:
                if self.isSameAnswerGPT(answer, answerOption):
                    print("has such answer")
                    return self.addToTree(QnA, parentNode, currentNode.answers[answerOption], answer)
                
            print("doesnt have such answer")
            if len(QnA) > 0:
                currentNode.answers[answer] = Node(QnA[0]["question"], parent=currentNode, answers={})
                return self.addToTree(QnA, parentNode, currentNode.answers[answer], answer)
            else:
                return parentNode
            
        else:
            if skipQuestionCompare:
                print("different question skip compare")
            print("different question")
            if currentNode.parent != None:
                #QnA = QnA[1:]
                print("previous answer: ", previousAnswer)
                currentNode.parent.answers[(previousAnswer + "-" + question)] = Node(question, parent=currentNode.parent, answers={})
                return self.addToTree(QnA, parentNode, currentNode.parent.answers[(previousAnswer + "-" + question)], previousAnswer, skipQuestionCompare=True)
            else:
                print("loop 1")
                found = False
                for answerOption in currentNode.answers:
                    print("loop 2")
                    print("comparing: ", QnA[0]["question"], answerOption[5:])
                    if self.isSameQuestionGPT(QnA[0]["question"], answerOption[5:]) and not skipQuestionCompare:
                        print("loop 3")
                        found = True
                        return self.addToTree(QnA, parentNode, currentNode.answers[answerOption], answer)
                if not found:
                    print("loop 4")
                    currentNode.answers[("none-" + QnA[0]["question"])] = Node(question, parent=currentNode, answers={})
                    return self.addToTree(QnA, parentNode, currentNode.answers[("none-" + QnA[0]["question"])], answer) 

    
    # Function to get keys from values
    def get_keys_from_value(self, dictionary, search_value):
        keys_list = []
        for key, value in dictionary.items():
            if value == search_value:
                keys_list.append(key)
        return keys_list
    
    def print_decision_tree(self, node, indent=0):
        print('  ' * indent + "Question: " + node.name)
        for answer in node.answers:
            print('  ' * (indent + 1) + "Answer: " + answer)
            self.print_decision_tree(node.answers[answer], indent + 2)

    def getAuthkey(self, sender_userID):
        return self.whitelist[sender_userID]
    
    
    def extractAnswers(self, comments, questions):
        comments = directchatHistory.memoryPostProcess(comments, role1="Support agent", role2="Customer")

        #prompt = "I will provide you a set of questions and a conversation. Extract answers to these questions based on the conversation provided. Do not include questions in output. Each answer should be in new line. Provide an answer for EVERY question."
        prompt = "I will give you a list of questions:\n\n"
        
        #system_msg = "I will provide you a set of questions and a conversation. Each question will be provided in new line. Each question should have a corresponding answer. Output format should be: '- {answer 1}\n- {answer 2}:\n...'"
        system_msg = ""

        prompt += "\n".join(f"{index + 1}. {question}" for index, question in enumerate(questions))
        prompt = prompt + "\n\nAnswer ALL questions you are given, even if they are repeated. Give me answers (in first person) to ALL of these questions above based on this conversation:"
        prompt = prompt + "\n\n" + comments

        prompt += "\n\n" + "Lets think step by step.\nYou will be answering questions. Output format should be:\n1. {answer to question 1}\n2. {answer to question 2}\n3. {answer to question 3}\n... \n\nOutput should only have answers. Number of answers should be the same as number of questions I give you."

        print(prompt)

        response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=[{"role": "user", "content": prompt}])
        answersExtracted = response["choices"][0]["message"]["content"]
        print("RAW ANSWERS:\n", answersExtracted)
        lines = answersExtracted.split('\n')
        answers = [line.strip('- ').strip() for line in lines if line.startswith('- ') or line.startswith('-') or line != '\n']
        answers = [answer.split('. ', 1)[1] for answer in answers]

        return answers

    def extractQuestions(self, comments):
        comments = directchatHistory.memoryPostProcess(comments, role1="Support agent", role2="Customer")

        prompt = "My goal is to create a set of questions which I can ask everytime someone has an issue, to figure out what is the issue. For the conversation below, provide a set of questions I can ask next time to figure out if someone is experiencing this exact issue. DO NOT make up questions, only extract from the conversation below."

        system_msg = "You will be given a conversation between support agent and customer. Do not write in dialogue. Output format should be: '- {question 1}\n- {question 2}:\n...'"

        user_msg = prompt + "\n\n" + comments

        response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=[{"role": "system", "content": system_msg},
                                                {"role": "user", "content": user_msg}])
        questionsExtracted = response["choices"][0]["message"]["content"]

        lines = questionsExtracted.split('\n')
        questions = [line.strip('- ').strip() for line in lines if line.startswith('- ') or line.startswith('-') or line.startswith('') or line != '\n']
        #questions.insert(0, "Can you please provide more information about the issue you are facing?")

        return questions


    def endConversation(self, sender_userID, recipient_userID):
        authKey = self.getAuthkey(sender_userID)

        lastComment = databaseHandler.get_user_last_comment(sender_userID, recipient_userID)
        print(recipient_userID)
        comments = directchatHistory.getAllComments(20, recipient_userID, authKey)
        comments = directchatHistory.getLastTopic(comments)
        if lastComment == None:
            lastComment = comments[-1]
        elif comments[-1] != lastComment:
            try:
                lastCommentIndex = comments.index(lastComment)
            except ValueError:
                lastCommentIndex = -1
            comments = comments[lastCommentIndex + 1:]

            lastComment = comments[-1]

        print("last comments topic:", comments)
        print("last comment", lastComment)

        databaseHandler.insert_last_comment(sender_userID, recipient_userID, lastComment)

        extractedQuestions = self.extractQuestions(comments)
        extractedAnswers = self.extractAnswers(comments, extractedQuestions)
        
        min_length = min(len(extractedQuestions), len(extractedAnswers))
        extractedQuestions = extractedQuestions[:min_length]
        extractedAnswers = extractedAnswers[:min_length]

        print("Extracted questions:\n")
        for question in extractedQuestions:
            print(question)
        print("Extracted answers:\n")
        for answer in extractedAnswers:
            print(answer)

        
        QnA = []
        for index, question in enumerate(extractedQuestions):
            QnA.append({"question": question, "answer": extractedAnswers[index]})
        """
        QnA = []
        QnA.append({"question": "Can you please provide more information about the problem you are facing?", "answer": "I do not see my emails. I am a new customer."})
        QnA.append({"question": "Can you send a screenshot of the issue?", "answer": "Here it is. [screenshot]"})
        QnA.append({"question": "Have you connected your personal inbox?", "answer": "I have not."})
        QnA.append({"question": "Are you seeing a spinner or any loading indicator?", "answer": "Yes i see it."})
        QnA.append({"question": "Do you see your emails them after waiting a few minutes?", "answer": "Ah yes, I can see them now."})
        
        newTree = self.addToTree(QnA, self.root, self.root, QnA[0]["answer"])
        self.print_decision_tree(newTree)

        QnA = []
        QnA.append({"question": "Is there any emails showing in your personal inbox?", "answer": "No."})
        QnA.append({"question": "Can you send a screenshot of the issue?", "answer": "Here it is. [screenshot]"})
        QnA.append({"question": "Have you connected your personal inbox?", "answer": "I have not."})
        QnA.append({"question": "Are you seeing a spinner or any loading indicator?", "answer": "Yes i see it."})
        QnA.append({"question": "Do you see your emails them after waiting a few minutes?", "answer": "Ah yes, I can see them now."})
        
        newTree = self.addToTree(QnA, self.root, self.root, QnA[0]["answer"])
        self.print_decision_tree(newTree)

        QnA = []
        QnA.append({"question": "Is there any emails showing in your personal inbox?", "answer": "No."})
        QnA.append({"question": "Can you send a screenshot of the issue?", "answer": "Here it is. [screenshot]"})
        QnA.append({"question": "When did you connect your personal inbox or other inboxes you have imn your account? Also tell me how did you do that? Tell me specific steps.", "answer": "about 3 hours ago."})
        QnA.append({"question": "Are you seeing a spinner or any loading indicator?", "answer": "Yes i see it."})
        QnA.append({"question": "Do you see your emails them after waiting a few minutes?", "answer": "Ah yes, I can see them now."})

        newTree = self.addToTree(QnA, self.root, self.root, QnA[0]["answer"])
        self.print_decision_tree(newTree)

        QnA = []
        QnA.append({"question": "Is there any emails showing in your personal inbox?", "answer": "No."})
        QnA.append({"question": "Can you send a screenshot of the issue?", "answer": "Here it is. [screenshot]"})
        QnA.append({"question": "Have you connected your personal inbox?", "answer": "about 3 hours ago."})
        QnA.append({"question": "Are you seeing a spinner or any loading indicator?", "answer": "No there is no spinner or loading indicator."})
        QnA.append({"question": "Does it show up after a few moments", "answer": "Ah yes, I can see it now."})
        
        newTree = self.addToTree(QnA, self.root, self.root, QnA[0]["answer"])
        self.print_decision_tree(newTree)"""
        #print("tree printed: ")
        #self.print_tree(newTree)
        #self.getSuggestedQuestion(newTree, "")
        #print(newTree)

        newTree = self.addToTree(QnA, self.root, self.root, QnA[0]["answer"])
        self.print_decision_tree(newTree)

        """# Serialize the root node
        serialized_root = self.serialize_node(newTree)

        # Convert the serialized data to JSON
        json_data = json.dumps(serialized_root, indent=2)
        print(json_data)

        # Deserialize JSON data back to a Node object
        parsed_data = json.loads(json_data)
        deserialized_root = self.deserialize_node(parsed_data)
        print(deserialized_root)
        self.print_decision_tree(deserialized_root)"""

        databaseHandler.insert_decision_tree(sender_userID, newTree, "support")
        self.print_decision_tree(databaseHandler.get_decision_tree(sender_userID, "support"))

        return '\n'.join(extractedQuestions)
        #return "Done"
    
#ts = TroubleshootHandler(keys.openAI_APIKEY)
#ts.endConversation("user_24564769", "user_24661115")
#ts.getSuggestedQuestion(ts.rootnode, "")