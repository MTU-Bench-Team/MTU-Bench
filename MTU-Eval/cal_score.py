from util import *

def score(predictions, references, ids, splits) -> dict:
    data_all = split_data(predictions, references, ids, splits)
    # S-S
    tool_correct_cnt, param_correct_cnt = 0, 0
    data = data_all['S-S']
    for prediction, reference, item_id in zip(data["predictions"], data["references"], data["ids"]):
        pre_action, pre_input = get_predict_SIN(prediction)
        target_action = list(reference.keys())[0]
        target_input = reference[target_action]
        target_input = {key: str(value).lower() for key, value in target_input.items()}
        pre_input = {key: str(value).lower() for key, value in pre_input.items()}
        if pre_action == target_action:
            tool_correct_cnt += 1
            if compare_dicts(target_input, pre_input):
                param_correct_cnt += 1
    tool_selection_acc = round(tool_correct_cnt / len(data["predictions"]) * 100, 2)
    param_selection_acc = round(param_correct_cnt / len(data["predictions"]) * 100, 2)
    scores_s_s = dict(
        tool_selection_acc=tool_selection_acc,
        param_selection_acc=param_selection_acc,
        average_score=round((tool_selection_acc + param_selection_acc) / 2 * 100, 2)
    )

    # S-M
    data = data_all['S-M']
    num_acc_scores, order_acc_scores = [], []
    for prediction, reference, item_id in zip(data["predictions"], data["references"], data["ids"]):
        target_action = reference
        pre_action = get_target_SIN_MUL(prediction)
        num_acc_hard, pre_action_new = calculate_num_acc_hard(pre_action, target_action)
        order_acc_hard = calculate_order_acc(list(pre_action_new.keys()), list(target_action.keys()))
        num_acc_scores.append(num_acc_hard)
        order_acc_scores.append(order_acc_hard)
    num_acc = round(sum(num_acc_scores) / len(num_acc_scores) * 100, 2)
    order_acc = round(sum(order_acc_scores) / len(order_acc_scores) * 100, 2)
    scores_s_m = dict(
        num_acc=num_acc,
        order_acc=order_acc,
        average_score=round((num_acc + order_acc) / 2 * 100, 2)
    )

    # M-S
    data = data_all['M-S']
    tool_correct_cnt, param_correct_cnt, is_correct = 0, 0, False
    success_dialog = {}
    for prediction, reference, item_id in zip(data["predictions"], data["references"], data["ids"]):
        diag_id, round_idx = item_id.rsplit("_", 1)[0], item_id.rsplit("_", 1)[1]
        pre_action, pre_input = get_predict_SIN(prediction)
        target_action = list(reference.keys())[0]
        target_input = reference[target_action]
        target_input = {key: str(value).lower() for key, value in target_input.items()}
        pre_input = {key: str(value).lower() for key, value in pre_input.items()}
        if pre_action == target_action:
            tool_correct_cnt += 1
            if compare_dicts(target_input, pre_input):
                is_correct = True
                param_correct_cnt += 1
        convo_list = success_dialog.get(diag_id, [])
        while len(convo_list) <= round_idx:
            convo_list.append(None)
        if is_correct:
            convo_list[round_idx] = 1
        else:
            convo_list[round_idx] = 0
        success_dialog[diag_id] = convo_list

    success_cnt, turn_rates, soft_turn_rates, task_process_rates = 0, [], [], [], []
    for id, pres in success_dialog.items():
        if sum(pres) == len(pres):
            success_cnt += 1

        _, turn_success_rate = calculate_turn_success_rate(pres)
        soft_turn_rates.append(turn_success_rate)
        turn_rates.append(sum(pres) / len(pres))
        task_process_rates.append(count_continuous_ones(pres))

    tool_selection_acc = round(tool_correct_cnt / len(data["predictions"]) * 100, 2)
    param_selection_acc = round(param_correct_cnt / len(data["predictions"]) * 100, 2)
    turn_rate = round(sum(turn_rates) / len(turn_rates) * 100, 2)
    soft_turn_rate = round(sum(soft_turn_rates) / len(soft_turn_rates) * 100, 2)
    task_success_rate = round(success_cnt / len(success_dialog) * 100, 2)
    task_process_rate = round(sum(task_process_rates) / len(task_process_rates) * 100, 2)

    scores_m_s = dict(
        tool_selection_acc=tool_selection_acc,
        param_selection_acc=param_selection_acc,
        turn_rate=turn_rate,
        soft_turn_rate=soft_turn_rate,
        task_success_rate=task_success_rate,
        task_process_rate=task_process_rate
    )

    # M-M
    data = data_all['M-M']
    success_dialog, num_accs, order_accs = {}, [], []
    for prediction, reference, item_id in zip(data["predictions"], data["references"], data["ids"]):
        diag_id, round_idx = item_id.rsplit("_", 1)[0], item_id.rsplit("_", 1)[1]

        target_action = reference
        pre_action = get_target_SIN_MUL(prediction)
        num_acc_hard, pre_action_new = calculate_num_acc_hard(pre_action, target_action)
        order_acc_hard = calculate_order_acc(list(pre_action_new.keys()), list(target_action.keys()))
        num_accs.append(num_acc_hard)
        order_accs.append(order_acc_hard)
        is_correct = True if order_acc_hard == 1 and num_acc_hard == 1 else False
        convo_list = success_dialog.get(diag_id, [])
        while len(convo_list) <= round_idx:
            convo_list.append(None)
        if is_correct:
            convo_list[round_idx] = 1
        else:
            convo_list[round_idx] = 0
        success_dialog[diag_id] = convo_list

    success_cnt, turn_rates, soft_turn_rates, task_process_rates = 0, [], [], [], []
    for id, pres in success_dialog.items():
        if sum(pres) == len(pres):
            success_cnt += 1

        _, turn_success_rate = calculate_turn_success_rate(pres)
        soft_turn_rates.append(turn_success_rate)
        turn_rates.append(sum(pres) / len(pres))
        task_process_rates.append(count_continuous_ones(pres))

    num_acc = round(sum(num_accs) / len(num_accs) * 100, 2)
    order_acc = round(sum(order_accs) / len(order_accs) * 100, 2)
    turn_rate = round(sum(turn_rates) / len(turn_rates) * 100, 2)
    soft_turn_rate = round(sum(soft_turn_rates) / len(soft_turn_rates) * 100, 2)
    task_success_rate = round(success_cnt / len(success_dialog) * 100, 2)
    task_process_rate = round(sum(task_process_rates) / len(task_process_rates) * 100, 2)

    scores_m_m = dict(
        num_acc=num_acc,
        order_acc=order_acc,
        turn_rate=turn_rate,
        soft_turn_rate=soft_turn_rate,
        task_success_rate=task_success_rate,
        task_process_rate=task_process_rate
    )

    return {"S-S": scores_s_s, "S-M": scores_s_m, "M-S": scores_m_s, "M-M": scores_m_m}










