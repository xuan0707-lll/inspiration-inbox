"""Build one of the Apple Shortcuts for saving video shares to Obsidian."""
import argparse
from pathlib import Path
import plistlib
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

random_id = '2CD67EDD-0A03-4213-BD4E-55BCC133B2E8'
intent_id = '22E7F02B-B24C-4C3E-AB4A-8179F1127702'
text_id = '999BA48D-4DCA-4256-84A4-69773A13F298'
encode_id = 'BD421061-410D-45B9-B376-2FC11E6C37AE'
url_id = '17002160-ED19-4EFF-8F6D-35A039B299DB'


def output_token(identifier, name):
    return {'Type': 'ActionOutput', 'OutputUUID': identifier, 'OutputName': name}


def variable(value):
    return {'WFSerializationType': 'WFTextTokenAttachment', 'Value': value}


def token_string(template, tokens):
    indexes = [index for index, value in enumerate(template) if value == '\ufffc']
    if len(indexes) != len(tokens):
        raise ValueError('快捷指令变量数量与模板不符。')
    return {'WFSerializationType': 'WFTextTokenString', 'Value': {
        'string': template,
        'attachmentsByRange': {f'{{{index}, 1}}': token for index, token in zip(indexes, tokens)},
    }}


def control_center_actions():
    actions = []

    def add(identifier, name='', **parameters):
        action_id = str(uuid5(NAMESPACE_URL, f'inspiration-control/{len(actions)}')).upper()
        if name:
            parameters['UUID'] = action_id
        actions.append({'WFWorkflowActionIdentifier': 'is.workflow.actions.' + identifier,
                        'WFWorkflowActionParameters': parameters})
        return output_token(action_id, name)

    def if_missing(value):
        group = str(uuid5(NAMESPACE_URL, f'inspiration-control/if/{len(actions)}')).upper()
        add('conditional', GroupingIdentifier=group, WFControlFlowMode=0, WFCondition=101,
            WFInput={'Type': 'Variable', 'Variable': variable(value)})
        return group

    incoming = {'Type': 'ExtensionInput'}
    group = if_missing(incoming)
    add('getclipboard', 'Clipboard')
    add('conditional', GroupingIdentifier=group, WFControlFlowMode=1)
    add('gettext', 'Text', WFTextActionText=token_string('\ufffc', [incoming]))
    share = add('conditional', 'If Result', GroupingIdentifier=group, WFControlFlowMode=2)
    links = add('text.match', 'Matches', text=token_string('\ufffc', [share]),
                WFMatchTextPattern=r'https://(?:[a-z0-9-]+\.)*(?:douyin\.com|iesdouyin\.com|bilibili\.com|b23\.tv|xiaohongshu\.com|xhslink\.(?:com|cn))/[^\s<>]+',
                WFMatchTextCaseSensitive=False, ShowWhenRun=False)
    invalid = if_missing(links)
    add('notification', WFNotificationActionTitle='存到灵感库',
        WFNotificationActionBody='请先复制抖音、B 站或小红书的分享链接。', WFNotificationActionSound=False)
    add('exit')
    add('conditional', GroupingIdentifier=invalid, WFControlFlowMode=2)
    group = if_missing(incoming)
    add('gettext', 'Text', WFTextActionText='')
    add('conditional', GroupingIdentifier=group, WFControlFlowMode=1)
    add('ask', 'Provided Input', WFInputType='Text',
        WFAskActionPrompt='我想怎么用？可以留空。', WFAskActionDefaultAnswer='')
    intent = add('conditional', 'If Result', GroupingIdentifier=group, WFControlFlowMode=2)
    random = add('number.random', 'Random Number', WFRandomNumberMinimum=100000000,
                 WFRandomNumberMaximum=999999999)
    body = add('gettext', 'Text', WFTextActionText=token_string(inbox_text, [intent, share]))
    encoded = add('urlencode', 'URL Encoded Text', WFEncodeMode='Encode',
                  WFInput=token_string('\ufffc', [body]))
    address = add('url', 'URL', WFURLActionURL=token_string(uri, [random, encoded]))
    add('openurl', WFInput=variable(address))
    return actions


inbox_text = '灵感分享 v1\n\ufffc\n---分享链接---\n\ufffc'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
parser.add_argument('--vault', default='灵感与素材')
options = parser.parse_args()
vault = quote(options.vault, safe='')
prefix = quote('手机分享收件箱/视频分享-', safe='')
uri = f'obsidian://new?vault={vault}&file={prefix}\ufffc.md&silent=true&content=\ufffc'
workflow = {
    'WFWorkflowClientVersion': '3036.0.4',
    'WFWorkflowMinimumClientVersion': 900,
    'WFWorkflowMinimumClientVersionString': '900',
    'WFWorkflowTypes': ['ActionExtension'],
    'WFWorkflowInputContentItemClasses': ['WFStringContentItem', 'WFURLContentItem'],
    'WFWorkflowIcon': {'WFWorkflowIconStartColor': 463140863, 'WFWorkflowIconGlyphNumber': 59511},
    'WFWorkflowActions': control_center_actions(),
}
with options.output.open('wb') as file:
    plistlib.dump(workflow, file, fmt=plistlib.FMT_BINARY)
