import re
import json
import numpy as np
from difflib import SequenceMatcher
import math

def split_data(predictions, references, ids, splits):
    data_all = {split: {'predictions': [], 'references': [], 'ids': []} for split in ['S-S', 'S-M', 'M-S', 'M-M']}

    for prediction, reference, id, split in zip(predictions, references, ids, splits):
        data_all[split]['predictions'].append(prediction)
        data_all[split]['references'].append(reference)
        data_all[split]['ids'].append(id)
    return data_all

def convert_to_json_compatible_string(input_str):
    temp_str = input_str.replace("\\'", "__SINGLE_QUOTE__")
    temp_str = re.sub(r"^'(.*)'$", r'"\1"', temp_str)  # 替换字符串两端的单引号
    temp_str = temp_str.replace("'", '"')
    temp_str = temp_str.replace('__SINGLE_QUOTE__', "\\'")
    temp_str = temp_str.replace("\\'", "\\\\'")
    return temp_str

def get_input(raw_str):
    matches = re.findall(r'\{.*?\}', raw_str)
    dict_list = []
    for match in matches:
        dict_list.append(match)
    return matches[0]

def normalize_value(value):
    value = value.replace('my ', '')
    num_to_word = {'0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
                   '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten'}
    for num, word in num_to_word.items():
        value = value.replace(num, word)
    value = value.replace('findprovider.', 'bookappointment.')
    date_to_day = {'2024-01-04': 'monday', '2024-01-05': 'tuesday', '2024-01-06': 'wednesday',
                   '2024-01-07': 'thursday', '2024-01-08': 'friday', '2024-01-09': 'saturday',
                   '2024-01-10': 'sunday'}
    for date, day in date_to_day.items():
        value = value.replace(date, day).replace('today', day)

    return value

def compare_dicts(dict1, dict2):
    dict1 = {key: value for key, value in dict1.items() if value != 'hotel'}
    dict2 = {key: value for key, value in dict2.items() if value != 'hotel'}
    if len(dict1) != len(dict2):
        return False
    for key, value1 in dict1.items():
        if key not in dict2:
            return False
        value2 = dict2[key]
        norm_value1 = normalize_value(value1)
        norm_value2 = normalize_value(value2)
        if norm_value1 not in norm_value2:
            return False

    return True

def get_predict_SIN(response):
    response = response.replace('Action', '\nAction').replace('Action Input', '\nAction Input').replace('\n\n',
                                                                                                        '\n')
    if "\nAction" not in response or "\nAction Input" not in response:
        action, input_dict = "", {}
    else:
        action = response.split("\nAction:")[1].split("\nAction Input:")[0].strip().strip("\n")
        action_input = response.split("\nAction Input:")[1].strip()

        action_input = action_input.rsplit("}", 1)[0] + "}"
        action_input = action_input.replace("\n", "")
        action_input = action_input.replace("True", "true").replace("False", "false")
        action_input = get_input(action_input)
        try:
            input_dict = json.loads(action_input)
        except:
            try:
                input_dict = json.loads(convert_to_json_compatible_string(action_input))
            except:
                action = ""
                input_dict = {}
    if 'None' in action:
        action, input_dict = "", {}
    if ',' in action:
        action = action.split(',')[0].strip()
    return action, input_dict

def get_target_SIN_MUL(response):
    response = response.replace('Action', '\nAction').replace('Action Input', '\nAction Input').replace('\n\n',
                                                                                                        '\n')
    action_dict = {}
    thought = response.split("\nAction")[0].replace("Thought: ", "")
    actions = response.replace("Thought: " + thought, "").split("\nAction: ")[1:]
    for action in actions:
        if 'The name of the API to be called.' in action:
            continue
        if "Please provide your" in action:
            action = action.split("Please provide your")[0].strip("\n")
        action_ = action.strip("\n")
        act = action_.split("\nAction Input")[0].strip().strip("\n").replace("\"", "")
        input = action_.split("\nAction Input:")[1].strip().replace("\n  ", "").split("}")[0] + "}".replace("\n",
                                                                                                            "")
        input = input.replace("True", "true").replace("False", "false")
        try:
            input_dict = json.loads(input)
        except:
            input_dict = {}
        action_dict[act] = input_dict
    return action_dict

def calculate_num_acc_hard(pred, gt):
    pred = {key.strip(): value for key, value in pred.items()}
    gt = {key.strip(): value for key, value in gt.items()}
    if pred == {} and gt == {}:
        return 1, {}
    elif pred == {} or gt == {}:
        pred_new = {key: value for key, value in pred.items()}
        return 0, pred_new
    pred_new = {}
    for tool in gt:
        if tool not in pred:
            continue
        gt_input = gt[tool]
        pre_input = pred[tool]

        gt_input = {key: str(value).lower() for key, value in gt_input.items()}
        pre_input = {key: str(value).lower() for key, value in pre_input.items()}

        if not compare_dicts(pre_input, gt_input):
            pred_new[tool + "wrong"] = pred[tool]
        else:
            pred_new[tool] = pred[tool]

    pred_set = set(list(pred_new.keys()))
    gt_set = set(list(gt.keys()))
    intersection = pred_set.intersection(gt_set)
    union = pred_set.union(gt_set)
    num_acc = len(intersection) / len(union) if len(union) > 0 else 0
    return num_acc, pred_new

def calculate_order_acc(Pred, GT):
    Pred = [item.strip() for item in Pred]
    GT = [item.strip() for item in GT]

    if Pred == GT:
        return 1.0
    elif Pred == [] or GT == []:
        return 0.0
    matcher = SequenceMatcher(None, GT, Pred)
    match = matcher.find_longest_match(0, len(GT), 0, len(Pred))

    lcr = match.size
    i = match.b
    pred_len = len(Pred)
    t = np.cos((np.pi / 2) * (i / pred_len))
    gt_toolnum = len(GT)
    order_acc = t * lcr / gt_toolnum
    return order_acc

def calculate_turn_success_rate(results_list):
    last_incorrect_idx = -1
    turn_success_rates = []

    for j, result in enumerate(results_list):
        if result == 0:
            turn_success_rate = 0
            last_incorrect_idx = j
        else:
            if last_incorrect_idx == -1:
                turn_success_rate = 1
            else:
                distance = j - last_incorrect_idx
                turn_success_rate = 1 - math.exp(-(distance))
        turn_success_rates.append(turn_success_rate)
    average_turn_success_rate = sum(turn_success_rates) / len(turn_success_rates)

    return turn_success_rates, average_turn_success_rate

def count_continuous_ones(lst):
    count = 0
    for num in lst:
        if num == 1:
            count += 1
        else:
            break
    return count / len(lst)


