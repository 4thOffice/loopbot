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
import time

class TroubleshootHandler:

    root = Node("Can you please provide more information about the issue you are facing?", answers={}, type="Question")

    def __init__(self, openAI_APIKEY):
        self.openAI_APIKEY = openAI_APIKEY
        os.environ['OPENAI_API_KEY'] = openAI_APIKEY
        with open('whitelist.json', 'r') as file:
            self.whitelist = json.load(file)

    def timeoutOpenAICall(self, user_msg, system_msg):
        start_time = time.time()
        response = None
        
        while time.time() - start_time < 5:
            try:
                # Make the API call
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg}
                    ]
                )
                break  # If successful, exit the loop
            except Exception as e:
                print(f"Error occurred: {e}")
                time.sleep(1)  # Wait for 1 second before retrying
        if response is not None:
            return response
        else:
            print("OpenAI API call timed out.")

    def isSameQuestionGPT(self, question1, question2, context, same=False):
        prompt = "I will provide you a question 1 and question 2."

        if same:
            system_msg = "You will be deciding whether 2 questions you will be given are the same. Output should ONLY be yes/no"
        else:
            system_msg = "You will be deciding whether 2 questions you will be given are generally similar. They have to ask for generally similar thing, they can be posed differently. Output should ONLY be yes/no"

        prompt += "\n\nQuestion 1: " + question1
        prompt += "\nQuestion 2: " + question2 + "\n\n"
        prompt += "Context conversation:\n" + context

        response = self.timeoutOpenAICall(prompt, system_msg)
        #response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
        #                                        messages=[{"role": "system", "content": system_msg},
        #                                        {"role": "user", "content": prompt}])
        answer = response["choices"][0]["message"]["content"]
        answer = answer.lower()
        print("-------------------------------")
        print("question1: ", question1)
        print("question2: ", question2)
        time.sleep(1)

        embeddingScore = self.isSameQuestion(question1, question2)
        
        if ("yes" in answer or embeddingScore < 0.35) and embeddingScore <= 0.8:
            print("score: ", response["choices"][0]["message"]["content"], embeddingScore)
            print("-------------------------------")
            return True
        print("score: ", response["choices"][0]["message"]["content"], embeddingScore)
        print("-------------------------------")
        return False
    
    def isSameAnswerGPT(self, answer1, answer2, question, context):
        prompt = "I will provide you answer 1 and answer 2. Figure out if the jist of both answers is similar. If it is similar, print 'yes' or else print 'no'."
        #Follow these steps in order to decide if answers are similar enough: From the answer, extract only the most important information. Figure out if these informations are somewhat similar to each other. If they are say 'yes' if not say 'no'"

        system_msg = "You will be deciding whether 2 answers you will be given are GENERALLY similar - they dont have to be exactly the same. Output should ONLY be yes/no"

        prompt += "\n\nQuestion: " + question
        prompt += "\nAnswer 1: " + answer1
        prompt += "\nAnswer 2: " + answer2 + "\n\n"
        prompt += "Context conversation:\n" + context

        #print(prompt)
        response = self.timeoutOpenAICall(prompt, system_msg)
        #response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
        #                                        messages=[{"role": "system", "content": system_msg},
        #                                        {"role": "user", "content": prompt}])
        answer = response["choices"][0]["message"]["content"]
        answer = answer.lower()
        print("-------------------------------")
        print("question: ", question)
        print("answer 1: ", answer1)
        print("answer 2: ", answer2)
        time.sleep(1)
        embeddingScore = self.isSameAnswer(answer1, answer2)
        if ("yes" in answer or embeddingScore < 0.35) and embeddingScore <= 0.8:
            print("score: ", response["choices"][0]["message"]["content"], embeddingScore)
            print("-------------------------------")
            return True
        print("score: ", response["choices"][0]["message"]["content"], embeddingScore)
        print("-------------------------------")
        return False

    def isSameQuestion(self, question1, question2):
        evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
        distance = evaluator.evaluate_string_pairs(
            prediction=question1, prediction_b=question2
        )
        
        return distance["score"]

    def isSameAnswer(self, answer1, answer2):
        evaluator = load_evaluator("pairwise_embedding_distance", distance_metric=EmbeddingDistance.EUCLIDEAN)
        distance = evaluator.evaluate_string_pairs(
            prediction=answer1, prediction_b=answer2
        )
        
        return distance["score"]

    def getTroubleshootSuggestion(self, sender_userID, comments):
        comments = directchatHistory.memoryPostProcess(comments, role1="Support agent", role2="Customer")
        decision_tree_root = databaseHandler.get_decision_tree(sender_userID, "support")
        if decision_tree_root is None:
            print("decision tree is none")
            decision_tree_root = Node("Can you please provide more information about the issue you are facing?", answers={}, type="question")

        questions = self.extractAgentQuestions(comments)
        answers = self.extractCustomerAnswers(comments, questions)

        QnA = []
        for index, question in enumerate(questions):
            QnA.append({"question": question, "answer": answers[index]})
        print(QnA)
        formatted_qna = ""
        for pair in QnA:
            formatted_qna += f"Question: {pair['question']}\nAnswer: {pair['answer']}\n\n"

        self.print_decision_tree(decision_tree_root)
        return self.getSuggestedQuestion(decision_tree_root, QnA, comments)
        #return "\n".join(questions)
        return formatted_qna

    def getSuggestedQuestion(self, currentNode, QnA, context):
        if len(QnA) <= 0 or currentNode.type == "issueClassification":
            return currentNode.name

        print("---------------TROUBLESHOOT PATH-------------------")
        print("cc: ", currentNode.name)

        foundQuestion = False
        for index, qnaSet in enumerate(QnA):
            if self.isSameQuestionGPT(qnaSet["question"], currentNode.name, context, same=True):
                foundQuestion = True
                temp = QnA[index]
                QnA[index] = QnA[0]
                QnA[0] = temp
                break
                
        if foundQuestion:
            for answerOption in currentNode.answers:
                #answerOption = answerOption.split("[:]")[0]
                if self.isSameAnswerGPT(answerOption, QnA[0]["answer"], QnA[0]["question"], context):
                    return self.getSuggestedQuestion(currentNode.answers[answerOption], QnA[1:], context)
            return "I don't know how to troubleshoot further.\n-> unknown answer <-"        
        return currentNode.name + "\n-> unknown question <-"
        
    def addToTree(self, QnA, parentNode, currentNode, previousAnswer, context, classifiedIssue, skipQuestionCompare=False):
        if len(QnA) <= 0 or currentNode.type == "issueClassification":
            #print("parent node: ", parentNode)
            return parentNode

        question = QnA[0]["question"]
        answer = QnA[0]["answer"]
        #QnA = QnA[1:]

        if self.isSameQuestionGPT(question, currentNode.name, context):
            QnA = QnA[1:]
            print("same question")
            for answerOption in currentNode.answers:
                if self.isSameAnswerGPT(answer, answerOption, question, context):
                    print("has such answer")
                    return self.addToTree(QnA, parentNode, currentNode.answers[answerOption], answer, context, classifiedIssue)
                
            print("doesnt have such answer")
            if len(QnA) > 0:
                currentNode.answers[answer] = Node(QnA[0]["question"], parent=currentNode, answers={}, type="question")
                return self.addToTree(QnA, parentNode, currentNode.answers[answer], answer, context, classifiedIssue)
            else:
                currentNode.answers[answer] = Node(classifiedIssue, parent=currentNode, answers={}, type="issueClassification")
                return self.addToTree(QnA, parentNode, currentNode.answers[answer], answer, context, classifiedIssue)
            
        else:
            print("different question")
            if currentNode.parent != None:
                #QnA = QnA[1:]
                print("previous answer: ", previousAnswer)
                currentNode.parent.answers[(previousAnswer + "[-]" + question)] = Node(question, parent=currentNode.parent, answers={}, type="question")
                return self.addToTree(QnA, parentNode, currentNode.parent.answers[(previousAnswer + "[-]" + question)], previousAnswer, context, classifiedIssue, skipQuestionCompare=True)
            else:
                found = False
                for answerOption in currentNode.answers:
                    print("comparing: ", QnA[0]["question"], answerOption[5:])
                    if self.isSameQuestionGPT(QnA[0]["question"], answerOption[5:], context) and not skipQuestionCompare:
                        found = True
                        return self.addToTree(QnA, parentNode, currentNode.answers[answerOption], answer, context, classifiedIssue)
                if not found:
                    currentNode.answers[("none[-]" + QnA[0]["question"])] = Node(question, parent=currentNode, answers={}, type="question")
                    return self.addToTree(QnA, parentNode, currentNode.answers[("none[-]" + QnA[0]["question"])], answer, context, classifiedIssue) 

    
    # Function to get keys from values
    def get_keys_from_value(self, dictionary, search_value):
        keys_list = []
        for key, value in dictionary.items():
            if value == search_value:
                keys_list.append(key)
        return keys_list
    
    def print_decision_tree(self, node, indent=0):
        if node.type == "question":
            print('  ' * indent + "Question: " + node.name)
        else:
            print('  ' * indent + "Classified issue: " + node.name)
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

        response = self.timeoutOpenAICall(prompt, "")
        #response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
        #                                        messages=[{"role": "user", "content": prompt}])
        answersExtracted = response["choices"][0]["message"]["content"]
        #print("RAW ANSWERS:\n", answersExtracted)
        lines = answersExtracted.split('\n')
        answers = [line.strip('- ').strip() for line in lines if line.startswith('- ') or line.startswith('-') or line != '\n']
        answers = [answer.split('. ', 1)[1] for answer in answers]

        return answers

    def extractQuestions(self, comments):
        comments = directchatHistory.memoryPostProcess(comments, role1="Support agent", role2="Customer")

        prompt = "My goal is to create a set of questions which I can ask everytime someone has an issue, to figure out what is the issue. For the conversation below, provide a set of questions (in the same order as in the conversation) I can ask next time to figure out if someone is experiencing this exact issue. DO NOT make up questions, only extract from the conversation below. Give me ONLY MAXIMUM 3 most important questions."

        system_msg = "You will be given a conversation between support agent and customer. Do not write in dialogue. Output format should be: '- {question 1}\n- {question 2}:\n...'"

        user_msg = prompt + "\n\n" + comments
        
        response = self.timeoutOpenAICall(user_msg, system_msg)
        #response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
        #                                        messages=[{"role": "system", "content": system_msg},
        #                                        {"role": "user", "content": user_msg}])
        questionsExtracted = response["choices"][0]["message"]["content"]

        lines = questionsExtracted.split('\n')
        questions = [line.strip('- ').strip() for line in lines if line.startswith('- ') or line.startswith('-') or line.startswith('') or line != '\n']
        #questions.insert(0, "Can you please provide more information about the issue you are facing?")

        return questions
    
    def extractAgentQuestions(self, comments):
        prompt = "Extract only questions that support agent asked the customer. Exclude questions asked by the customer. If support agent did not ask any questions, just say so - do not make up questions!"

        system_msg = "You will be given a conversation between support agent and customer. Do not write in dialogue. Output format should be: '- {question 1}\n- {question 2}:\n...'"

        user_msg = prompt + "\n\nConversation:\n" + comments
        user_msg += "\n\nIf 'support agent' did not ask any questions, say 'no questions'\nIf 'support agent' is not in the conversation, say 'no questions'"

        print(user_msg)
        response = self.timeoutOpenAICall(user_msg, system_msg)
        #response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
        #                                        messages=[{"role": "system", "content": system_msg},
        #                                        {"role": "user", "content": user_msg}])
        questionsExtracted = response["choices"][0]["message"]["content"]

        lines = questionsExtracted.split('\n')
        questions = [line.lstrip('- ').strip() for line in lines if (line.startswith('- ') or line.startswith('-') or line.startswith('')) and "?" in line]
        #questions.insert(0, "Can you please provide more information about the issue you are facing?")

        return questions
    
    def extractCustomerAnswers(self, comments, questions):
        prompt = "I will give you a list of questions:\n\n"
        
        prompt += "\n".join(f"{index + 1}. {question}" for index, question in enumerate(questions))
        prompt = prompt + "\n\nAnswer ALL questions you are given, even if they are repeated. Give me customer answer (in first person) to ALL of these questions above based on this conversation. basically give me replies that customer gave to these questions.:"
        prompt = prompt + "\n\n" + comments

        prompt += "\n\n" + "Lets think step by step.\nYou will be providing answers to questions. Output format should be:\n1. {answer to question 1}\n2. {answer to question 2}...\n\nOutput should only have answers. Number of answers should be the same as number of questions I give you."

        #print(prompt)
        response = self.timeoutOpenAICall(prompt, "")
        #response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
        #                                        messages=[{"role": "user", "content": prompt}])
        answersExtracted = response["choices"][0]["message"]["content"]
        #print("RAW ANSWERS:\n", answersExtracted)
        lines = answersExtracted.split('\n')
        try:
            answers = [line.strip('- ').strip() for line in lines if line.startswith('- ') or line.startswith('-') or line != '\n']
            answers = [answer.split('. ', 1)[1] for answer in answers]
        except:
            return self.extractCustomerAnswers(comments, questions)

        return answers


    def endConversation(self, sender_userID, recipient_userID, classifiedIssue):
        authKey = self.getAuthkey(sender_userID)
        decision_tree_root = databaseHandler.get_decision_tree(sender_userID, "support")
        
        if decision_tree_root is None:
            print("decision tree is none")
            decision_tree_root = Node("Can you please provide more information about the issue you are facing?", answers={}, type="question")

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

        comments = directchatHistory.memoryPostProcess(comments, role1="Support agent", role2="Customer")
        newTree = self.addToTree(QnA, decision_tree_root, decision_tree_root, QnA[0]["answer"], comments, classifiedIssue=classifiedIssue)
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

        return '\n'.join(extractedQuestions)
        #return "Done"
    
#ts = TroubleshootHandler(keys.openAI_APIKEY)
#ts.endConversation("user_24564769", "user_24661115")
#ts.getSuggestedQuestion(ts.rootnode, "")