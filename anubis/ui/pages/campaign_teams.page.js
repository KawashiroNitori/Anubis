/**
 * Created by Nitori on 2017/4/9.
 */
import _ from 'lodash';

import { NamedPage } from '../misc/PageLoader';
import Notification from '../components/notification';
import { ConfirmDialog, ActionDialog } from '../components/dialog';

import * as util from '../misc/Util';
import tpl from '../utils/tpl';
import delay from '../utils/delay';
import i18n from '../utils/i18n';


const page = new NamedPage('campaign_teams', () => {
    const attendTeamDialog = new ActionDialog({
        $body: $('.dialog__body--attend-team > div'),
        onDispatch(action) {
            const $domainId = $('[name="domain_id"]');
            const $tid = $('[name="tid"]');
            if (action === 'ok') {
                if ($domainId.val() === '') {
                    $domainId.focus();
                    return false;
                }
                if ($tid.val() === '') {
                    $tid.focus();
                    return false;
                }
            }
            return true;
        },
    });
    attendTeamDialog.clear = function () {
        this.$dom.find('[name="domain_id"]').val('');
        this.$dom.find('[name="tid"]').val('');
        return this;
    };

    const ensureAndGetSelectedUsers = () => {
        const users = _.map(
            $('.campaign-teams tbody [type="checkbox"]:checked'),
            ch => ({
                id: $(ch).closest('tr').attr('data-id'),
                num: $(ch).closest('tr').attr('data-num'),
            }),
        );
        if (users.length === 0) {
            Notification.error(i18n('Please select at least one user to perform this operation.'));
            return null;
        }
        return {
            id: users.map(item => item.id),
            num: users.map(item => item.num),
        };
    };

    async function handleUpdateUserClick() {
        const users = ensureAndGetSelectedUsers();
        if (users === null) {
            return;
        }
        console.log(users);
        const action = await new ConfirmDialog({
            $body: tpl`
                <div class="typo">
                  <p>${i18n('Confirm update information for selected users?')}</p>
                  <p>${i18n('Their password will be reseted.')}</p>
                </div>`,
        }).open();
        if (action !== 'yes') {
            return;
        }
        try {
            await util.post('', {
                operation: 'update_user',
                team_id: users.id,
                team_num: users.num,
            });
            Notification.success(i18n('Selected users have been updated.'));
            await delay(2000);
            window.location.reload();
        } catch (error) {
            Notification.error(error.message);
        }
    }

    async function handleAttendTeamClick() {
        const users = ensureAndGetSelectedUsers();
        if (users === null) {
            return;
        }
        const action = await attendTeamDialog.clear().open();
        if (action !== 'ok') {
            return;
        }
        const domain_id = attendTeamDialog.$dom.find('[name="domain_id"]').val();
        const tid = attendTeamDialog.$dom.find('[name="tid"]').val();
        try {
            await util.post('', {
                operation: 'attend_team',
                domain_id,
                tid,
                team_num: users.num,
            });
            Notification.success(i18n('Selected teams has been attended.'));
            await delay(2000);
            window.location.reload();
        } catch (error) {
            Notification.error(error.message);
        }
    }

    $('[name="select_newbie"]').click(() => $('[data-newbie="True"]').prop('checked', true));
    $('[name="select_normal"]').click(() => $('[data-newbie!="True"]').prop('checked', true));
    $('[name="update_user"]').click(handleUpdateUserClick);
    $('[name="attend_team"]').click(handleAttendTeamClick);
});

export default page;
